#main3.py
import time
import logging
import math
from config import config_data
from user_input2 import user_config
from coinbase_auth import create_signed_request, fetch_historical_data
from coinbase_utils import fetch_product_stats, generate_signature
from bollinger_utils import calculate_bollinger_bands, determine_starting_sell_parameters, determine_starting_buy_parameters, determine_mean24
from order_utils import place_starting_open_sell_order, place_starting_open_buy_order, waiting_period_conditions, wait_for_order
from order_processing_utils import open_limit_sell_order_processing, open_limit_buy_order_processing, close_limit_buy_order_processing, close_limit_sell_order_processing, open_market_sell_order_processing, open_market_buy_order_processing, close_market_buy_order_processing, close_market_sell_order_processing
from compounding_utils import calculate_close_limit_buy_compounding_amt_Q, calculate_close_market_buy_compounding_amt_Q, calculate_close_limit_sell_compounding_amt_B, calculate_close_market_sell_compounding_amt_B, determine_next_close_size_Q_limit, determine_next_close_size_B_limit, determine_next_close_size_Q_market, determine_next_close_size_B_market, determine_next_open_size_B_limit, determine_next_open_size_Q_limit, determine_next_open_size_B_market, determine_next_open_size_Q_market,calculate_open_limit_sell_compounding_amt_B, calculate_open_market_sell_compounding_amt_B, calculate_open_limit_buy_compounding_amt_Q, calculate_open_market_buy_compounding_amt_Q
from repeating_cycle_utils import calculate_long_term_ma24, calculate_rsi, determine_open_order_prices, place_next_opening_cycle_sell_order, place_next_opening_cycle_buy_order, id_opening_order, place_next_closing_cycle_buy_order, place_next_closing_cycle_sell_order, id_closing_order
from cycle_set_utils import CycleSet, determine_starting_prices, place_starting_sell_buy_cycle_orders, place_starting_buy_sell_cycle_orders, place_next_sell_buy_cycle_orders, place_next_buy_sell_cycle_orders
from trading_record_manager import get_order_details # Add imports after modifying this module

# Configure logging
logging.basicConfig(filename='trading_bot.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')  # Create a log file

try:
    print("Initializing trading bot...")
    
    # Define your API credentials
    api_key = config_data["api_key"]
    api_secret = config_data["api_secret"]

    # Specify the product ID, chart interval ((in seconds), and other settings here
    product_id = user_config["product_id"]  # Replace with your product ID
    chart_interval = user_config["chart_interval"]  # Replace with your desired chart interval in seconds (e.g., 60 for 1-minute chart)
    num_intervals = user_config["num_intervals"]  # Replace with the number of intervals you want to fetch
    window_size = user_config["window_size"]  # Define the window size for calculating Bollinger Bands
    wait_period_unit = user_config["wait_period_unit"]  # Enter units for wait period interval ("minutes", "hours", "days")
    first_order_wait_period = user_config["first_order_wait_period"]  # Enter amount in wait_period_units for interval for wait period
    maker_fee = user_config["maker_fee"]  # The maker fee for user's pricing tier on Coinbase Advanced Trade
    taker_fee = user_config["taker_fee"]  # The taker fee for user's pricing tier on Coinbase Advanced Trade

    # Define order processing parameters dictionary with initialized values
    order_processing_params = {
        "total_received_Q_ols": None,
        "total_spent_B_ols": None,
        "total_received_B_olb": None,
        "total_spent_Q_olb": None,
        "total_received_B_clb": None,
        "total_spent_Q_clb": None,
        "total_received_Q_cls": None,
        "total_spent_B_cls": None,
        "total_received_Q_oms": None,
        "total_spent_B_oms": None,
        "total_received_B_omb": None,
        "total_spent_Q_omb": None,
        "total_received_B_cmb": None,
        "total_spent_Q_cmb": None,
        "total_received_Q_cms": None,
        "total_spent_B_cms": None,
    }

    # Define the api endpoint and payload (if applicable)
    endpoint = f'/api/v3/brokerage/products/{product_id}'  # Replace with the actual endpoint
    method = 'GET'
    body = ''  # Empty for GET requests

    # Create a signed request using your API credentials
    headers = create_signed_request(api_key, api_secret, method, endpoint, body)
    api_signature = generate_signature(api_secret, headers, product_id)

    print("API credentials configured successfully")

    # Define monitoring parameters for starting cycles
    interval = first_order_wait_period
    unit = wait_period_unit

    # Fetch the latest product stats from Coinbase API with error handling
    print("Fetching product stats...")
    product_stats = fetch_product_stats(product_id, api_key, headers)

    if product_stats is not None:
        print("Product stats fetched successfully")
        print(product_stats)

    # Fetch historical data for the specified chart interval
    print("Fetching historical data...")
    historical_data = fetch_historical_data(product_id, chart_interval, num_intervals)
    # Print the first few entries of historical_data for debugging
    print("Historical Data Sample:")
    for entry in historical_data[:5]:  # Print the first 5 entries as an example
        print(entry)
    if historical_data is not None:
        print("Historical data fetched successfully")

    # Extract the close prices from the historical data
    closing_prices = []

    for entry in historical_data:
        try:
            close_price = float(entry[4])
            closing_prices.append(close_price)
        except ValueError:
            # Handle invalid data (e.g., non-numeric values) here, if needed
            # You can print a message or take other appropriate actions
            pass

    # Now you have a list of floats in closing_prices

    # Get the latest close price ("last") from the historical data
    current_price = closing_prices[0]
    print("Current Price", current_price)

    # Define user input parameters
    starting_size_B = user_config["starting_size_B"]  # Replace with the appropriate value
    starting_size_Q = user_config["starting_size_Q"]  # Replace with the appropriate value
    profit_percent = user_config["profit_percent"]  # The desired profit percentage for the cycle
    compound_percent = user_config["compound_percent"]  # The desired compounding percentage
    compounding_option = user_config["compounding_option"]  # "100" for full compounding, "partial" for partial compounding

    # Define base and quote increments
    base_increment = product_stats["base_increment"]
    base_increment = float(base_increment)
    quote_increment = product_stats["quote_increment"]
    quote_increment = float(quote_increment)

    # Determine starting side based on user inputs
    if starting_size_B > 0:
        starting_side = "sell"
    elif starting_size_Q > 0:
        starting_side = "buy"
    else:
        raise ValueError("Invalid size inputs")

    print("Starting trading strategy...")

    max_retries = 5  # Set the maximum number of retries

    for _ in range(max_retries):

        # Determine 24 hour mean
        print("Determining 24 hour mean...")
        mean24 = determine_mean24()

        # Calculate Bollinger bands
        print("Calculating Bollinger bands...")
        upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, window_size, num_std_dev=2)

        # Determine if the market is favorable for a sell or buy order based on mean24
        print("Determining market favorability...")
        market_favorable_for_sell = current_price > mean24 and starting_size_B > 0
        market_favorable_for_buy = current_price < mean24 and starting_size_Q > 0

        if market_favorable_for_sell:
            print("Market is favorable for sell order")
            starting_price_sell = determine_starting_sell_parameters(current_price, upper_bb, starting_size_B, mean24)
            if starting_price_sell is not None:
                rounded_price = round((starting_price_sell * 0.995), -int(math.floor(math.log10(quote_increment))))

                # Ensure the rounded price is at least quote_increment
                if rounded_price < quote_increment:
                    rounded_price = quote_increment

                starting_price_buy = rounded_price  # Adjust the buy price
                print("Starting sell order price:", starting_price_sell, "Starting buy order price:", starting_price_buy)

        elif market_favorable_for_buy:
            print("Market is favorable for buy order")
            starting_price_buy = determine_starting_buy_parameters(current_price, lower_bb, starting_size_Q, mean24)
            if starting_price_buy is not None:
                rounded_price = round((starting_price_buy * 1.005), -int(math.floor(math.log10(quote_increment))))

                # Ensure the rounded price is at least quote_increment
                if rounded_price < quote_increment:
                    rounded_price = quote_increment

                starting_price_sell = rounded_price  # Adjust the sell price
                print("Starting sell order price:", starting_price_sell, "Starting buy order price:", starting_price_buy)
            
        else:
            print("Unable to calculate starting prices")
            pass # Add code to retry with new current price

    # Place the starting opening order(s)
    print("Placing the starting opening cycle order...")
    open_order_id_sell = place_starting_open_sell_order(product_id, starting_size_B, starting_price_sell)
    open_order_id_buy = place_starting_open_buy_order(product_id, product_stats, starting_size_Q, starting_price_buy, maker_fee)
    open_order_ids = [open_order_id_sell, open_order_id_buy]
    open_order_id = open_order_ids

    print("Starting opening cycle order(s) placed successfully:", open_order_id)

    # Check order(s) placed/filled
    print("Checking the starting opening cycle order status...")
    waiting_period, elapsed_time = waiting_period_conditions(wait_period_unit, first_order_wait_period)

    # Wait for the starting opening cycle order to complete
    print("Waiting for starting opening cycle order(s) to complete...")
    wait_for_order(api_key, api_secret, open_order_id)

    # Add later: Check for adverse market conditions and make adjustments if necessary
    # Add logic for adverse market conditions, criteria for cancelling order and placing closing market order, and placing new open order

    print("Starting opening cycle order completed successfully")

    # Process starting opening order amount spent, fees, and amount to be received
    print("Processing starting opening cycle order assets...")
    open_size_B = starting_size_B
    open_size_Q = starting_size_Q
    quote_increment = product_stats["quote_increment"]
    base_increment = product_stats["base_increment"]
    order_processing_params = open_limit_sell_order_processing(order_processing_params, open_size_B, starting_price_sell, maker_fee, quote_increment)
    order_processing_params = open_limit_buy_order_processing(order_processing_params, open_size_Q, starting_price_buy, maker_fee, base_increment)
    total_received_Q_ols = order_processing_params["total_received_Q_ols"] 
    total_spent_B_ols = order_processing_params["total_spent_B_ols"]
    total_received_B_olb = order_processing_params["total_received_B_olb"] 
    total_spent_Q_olb = order_processing_params["total_spent_Q_olb"]

    # Calculate starting (cycle 1) close cycle price(s)
    close_price_buy = starting_price_sell * (1 - profit_percent - (2 * maker_fee))
    close_price_sell = starting_price_buy * (1 + profit_percent + (2 * maker_fee))

    print("Calculating starting closing cycle prices...")

    # Calculate starting (cycle 1) close cycle compounding amount and next starting close cycle size(s)
    compounding_amt_Q_clb, no_compounding_Q_limit_clb = calculate_close_limit_buy_compounding_amt_Q(total_received_Q_ols, total_spent_B_ols, close_price_buy, maker_fee, quote_increment)
    compounding_amt_B_cls, no_compounding_B_limit_cls = calculate_close_limit_sell_compounding_amt_B(total_received_B_olb, total_spent_Q_olb, close_price_sell, maker_fee, base_increment)
    next_size_Q = determine_next_close_size_Q_limit(compounding_option, total_received_Q_ols, no_compounding_Q_limit_clb, compounding_amt_Q_clb, compound_percent)
    next_size_B = determine_next_close_size_B_limit(compounding_option, total_received_B_olb, no_compounding_B_limit_cls, compounding_amt_B_cls, compound_percent)

    print("Closing cycle compounding and next size calculated successfully")

    # Close order
    print("Placing the starting closing cycle order...")
    close_order_id_buy = place_next_closing_cycle_buy_order(api_key, api_secret, product_id, next_size_Q, maker_fee, close_price_buy)
    close_order_id_sell = place_next_closing_cycle_sell_order(api_key, api_secret, product_id, next_size_B, close_price_sell)
    close_order_ids = [close_order_id_buy, close_order_id_sell]
    close_order_id = close_order_ids

    print("Starting closing cycle order placed successfully:", close_order_id)

    # Check order(s) placed/filled
    print("Checking the starting closing cycle order status...")
    waiting_period, elapsed_time = waiting_period_conditions(wait_period_unit, first_order_wait_period)

    # Wait for the close order to complete
    print("Waiting for the starting closing cycle order to complete...")
    wait_for_order(api_key, api_secret, close_order_id)

    print("Starting closing cycle order completed successfully")

    # Process starting closing order amount spent, fees, and amount to be received
    print("Processing starting closing cycle order assets...")
    close_size_Q = next_size_Q
    close_size_B = next_size_B
    close_price_buy = starting_price_sell * (1 - profit_percent - (2 * maker_fee))
    close_price_sell = starting_price_buy * (1 + profit_percent + (2 * maker_fee))
    base_increment = product_stats["base_increment"]
    quote_increment = product_stats["quote_increment"]
    order_processing_params = close_limit_buy_order_processing(order_processing_params, close_size_Q, close_price_buy, maker_fee, base_increment)
    order_processing_params = close_limit_sell_order_processing(order_processing_params, close_size_B, close_price_sell, maker_fee, quote_increment)
    total_received_B_clb = order_processing_params["total_received_B_clb"]
    total_spent_Q_clb = order_processing_params["total_spent_Q-clb"]
    total_received_Q_cls = order_processing_params["total_received_Q_cls"]
    total_spent_B_cls = order_processing_params["total_spent_B_cls"]

    # Gather data for logic to determine prices for opening cycle orders for repeating cycles

    # Print statement to indicate bollinger band and long term 24 hr moving average calculations
    print("Calculating bollinger bands and long-term 24 hr moving average...")
    upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, user_config["window_size"], num_std_dev=2)
    long_term_ma24 = calculate_long_term_ma24(closing_prices)

    # Print statement to indicate current RSI calculation
    print("Calculating current RSI...")

    # Calculate current RSI
    rsi = calculate_rsi(product_id, chart_interval, length=20160)  # 15 days worth of 1-minute data
    current_rsi = rsi
    print("Current RSI:", current_rsi)

    # Determine new opening cycle prices
    open_price_sell, open_price_buy = determine_open_order_prices(closing_prices, long_term_ma24, profit_percent, upper_bb, lower_bb, current_rsi)

    # Calculate compounding amount(s) and sizes for next opening cycle orders
    print("Calculating compounding amount(s) and next opening cycle order sizes...")
    compounding_amount_B_ols, no_compounding_B_limit_ols = calculate_open_limit_sell_compounding_amt_B(total_received_B_clb, total_spent_Q_clb, close_price_sell, maker_fee, base_increment)
    compounding_amount_Q_olb, no_compounding_Q_limit_olb = calculate_open_limit_buy_compounding_amt_Q(total_received_Q_cls, total_spent_B_cls, close_price_buy, maker_fee, quote_increment)
    open_size_B = determine_next_open_size_B_limit(compounding_option, total_received_B_clb, no_compounding_B_limit_ols, compounding_amount_B_ols, compound_percent)
    open_size_Q = determine_next_open_size_Q_limit(compounding_option, total_received_Q_cls, no_compounding_Q_limit_olb, compounding_amount_Q_olb, compound_percent)

    # Initialize cycle count
    cycle_count = 1

    # Main trading loop (runs indefinitely until you manually stop it)
    while True:
        if cycle_count == 1:
            # For the first cycle, set open_size_B, open_size_Q, close_size_Q, and close_size_B directly
            open_size_B = starting_size_B
            open_size_Q = starting_size_Q
            close_size_Q = next_size_Q
            close_size_B = next_size_B
        else:
            # Calculate open_size_B and open_size_Q based on compounding logic for subsequent cycles
            open_size_B = determine_next_open_size_B_limit(compounding_option, total_received_B_clb, no_compounding_B_limit_ols, compounding_amount_B_ols, compound_percent) 
            open_size_Q = determine_next_open_size_Q_limit(compounding_option, total_received_Q_cls, no_compounding_Q_limit_olb, compounding_amount_Q_olb, compound_percent)
            
        # Place the opening orders of the repeating cycles using open_size_B and open_size_Q

        # Determine new opening cycle prices
        open_price_sell, open_price_buy = determine_open_order_prices(closing_prices, long_term_ma24, profit_percent, upper_bb, lower_bb, current_rsi)
        
        # Place opening orders and get order IDs
        print(f"Placing the opening cycle order for cycle {cycle_count}...")

        open_order_ids_sell, open_order_ids_buy = id_opening_order(api_key, api_secret, product_id, starting_side, open_size_B, open_size_Q, maker_fee, open_price_sell, open_price_buy)
        open_order_ids = open_order_ids_sell, open_order_ids_buy 
        print("Opening order IDs (Sell):", open_order_ids_sell)
        print("Opening order IDs (Buy):", open_order_ids_buy)
        
        print(f"Opening order(s) for cycle {cycle_count} placed successfully")

        # Wait for the opening order to complete
        print("Waiting for the opening order(s) to complete...")
        wait_for_order(api_key, api_secret, open_order_ids)
        
        print(f"Opening order(s) for cycle {cycle_count} completed successfully")

        # Process opening order amount spent, fees, and amount to be received
        print("Processing opening cycle order assets...")
        open_size_B = determine_next_open_size_B_limit(compounding_option, total_received_B_clb, no_compounding_B_limit_ols, compounding_amount_B_ols, compound_percent) 
        open_size_Q = determine_next_open_size_Q_limit(compounding_option, total_received_Q_cls, no_compounding_Q_limit_olb, compounding_amount_Q_olb, compound_percent)
        quote_increment = product_stats["quote_increment"]
        base_increment = product_stats["base_increment"]
        order_processing_params = open_limit_sell_order_processing(order_processing_params, open_size_B, open_price_sell, maker_fee, quote_increment)
        order_processing_params = open_limit_buy_order_processing(order_processing_params, open_size_Q, open_price_buy, maker_fee, base_increment)
        total_received_Q_ols = order_processing_params["total_received_Q_ols"] 
        total_spent_B_ols = order_processing_params["total_spent_B_ols"]
        total_received_B_olb = order_processing_params["total_received_B_olb"] 
        total_spent_Q_olb = order_processing_params["total_spent_Q_olb"]

        # Determine parameters for closing cycle order(s) based on opening cycle order(s)
        print("Determining closing cycle order parameters...")

        # Calculate closing cycle price(s)
        print("Calculating closing cycle prices...")
        close_price_buy = open_price_sell * (1 - profit_percent - (2 * maker_fee))
        close_price_sell = open_price_buy * (1 + profit_percent + (2 * maker_fee))

        # Calculate closing cycle compounding amount and next closing cycle size(s)
        compounding_amt_Q_clb, no_compounding_Q_limit_clb = calculate_close_limit_buy_compounding_amt_Q(total_received_Q_ols, total_spent_B_ols, close_price_buy, maker_fee, quote_increment)
        compounding_amt_B_cls, no_compounding_B_limit_cls = calculate_close_limit_sell_compounding_amt_B(total_received_B_olb, total_spent_Q_olb, close_price_sell, maker_fee, base_increment)
        close_size_Q = determine_next_close_size_Q_limit(compounding_option, total_received_Q_ols, no_compounding_Q_limit_clb, compounding_amt_Q_clb, compound_percent) 
        close_size_B = determine_next_close_size_B_limit(compounding_option, total_received_B_olb, no_compounding_B_limit_cls, compounding_amt_B_cls, compound_percent)
        
        print(f"Closing cycle order parameters determined for cycle {cycle_count}")

        # Place the closing order using close_size_B, close_size_Q, close_price_sell, close_price_buy
        print(f"Placing closing order for cycle {cycle_count}...")

        close_order_ids_buy, close_order_ids_sell = id_closing_order(api_key, api_secret, product_id, starting_side, starting_size_B, starting_size_Q, maker_fee, close_price_buy, close_price_sell)
        close_order_ids = close_order_ids_buy, close_order_ids_sell
        print("Closing order IDs (Buy):", close_order_ids_buy)
        print("Closing order IDs (Sell):", close_order_ids_sell)
        
        print(f"Closing order(s) for cycle {cycle_count} placed successfully")

        # Wait for the close order to complete
        print("Waiting for the closing order(s) to complete...")
        wait_for_order(api_key, api_secret, close_order_ids)
        
        print(f"Closing order(s) for cycle {cycle_count} completed successfully")

        # Print statement to indicate cycle status
        print("Cycle completed")

        # Process closing order amount spent, fees, and amount to be received
        print("Processing starting closing cycle order assets...")
        close_size_Q = determine_next_close_size_Q_limit(compounding_option, total_received_Q_ols, no_compounding_Q_limit_clb, compounding_amt_Q_clb, compound_percent) 
        close_size_B = determine_next_close_size_B_limit(compounding_option, total_received_B_olb, no_compounding_B_limit_cls, compounding_amt_B_cls, compound_percent)
        close_price_buy = open_price_sell * (1 - profit_percent - (2 * maker_fee))
        close_price_sell = open_price_buy * (1 + profit_percent + (2 * maker_fee))
        base_increment = product_stats["base_increment"]
        quote_increment = product_stats["quote_increment"]
        order_processing_params = close_limit_buy_order_processing(order_processing_params, close_size_Q, close_price_buy, maker_fee, base_increment)
        order_processing_params = close_limit_sell_order_processing(order_processing_params, close_size_B, close_price_sell, maker_fee, quote_increment)
        total_received_B_clb = order_processing_params["total_received_B_clb"]
        total_spent_Q_clb = order_processing_params["total_spent_Q-clb"]
        total_received_Q_cls = order_processing_params["total_received_Q_cls"]
        total_spent_B_cls = order_processing_params["total_spent_B_cls"]

        # Calculate compounding amount(s) and sizes for next opening cycle orders
        print("Calculating compounding amount(s) and next opening cycle order sizes...")
        compounding_amount_B_ols, no_compounding_B_limit_ols = calculate_open_limit_sell_compounding_amt_B(total_received_B_clb, total_spent_Q_clb, close_price_sell, maker_fee, base_increment)
        compounding_amount_Q_olb, no_compounding_Q_limit_olb = calculate_open_limit_buy_compounding_amt_Q(total_received_Q_cls, total_spent_B_cls, close_price_buy, maker_fee, quote_increment)
        open_size_B = determine_next_open_size_B_limit(compounding_option, total_received_B_clb, no_compounding_B_limit_ols, compounding_amount_B_ols, compound_percent) 
        open_size_Q = determine_next_open_size_Q_limit(compounding_option, total_received_Q_cls, no_compounding_Q_limit_olb, compounding_amount_Q_olb, compound_percent)

        # Add a delay before the next cycle
        time.sleep(1)
        print("Cycle completed and sleeping for the next iteration")
        
        # Define the stopping_condition_met variable
        stopping_condition_met = False

        # Check if stopping condition is met (e.g., based on external signals)
        if stopping_condition_met:
            break  # Exit the loop when the stopping condition is met
        print("Trading bot has been manually stopped or external stopping condition met")

        # Increment cycle count
        cycle_count += 1

except Exception as e:
    # Log any exceptions that occur
    logging.error(f"An error occurred: {str(e)}")
