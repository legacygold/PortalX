# cycle_set_utils.py
import threading
import time
from logging_config import app_logger, info_logger, error_logger
import math
import json
import requests
from coinbase_auth import config_data
from coinbase_utils import get_order_status, cancel_orders, get_decimal_places
from starting_input import user_config
from bollinger_utils import historical_data, determine_starting_sell_parameters, determine_starting_buy_parameters, determine_mean24
from order_utils import place_starting_open_sell_order, place_starting_open_buy_order, wait_for_order
from order_processing_utils import open_limit_sell_order_processing, open_limit_buy_order_processing, close_limit_buy_order_processing, close_limit_sell_order_processing
from compounding_utils import calculate_close_limit_buy_compounding_amt_Q, calculate_close_limit_sell_compounding_amt_B, determine_next_close_size_Q_limit, determine_next_close_size_B_limit, determine_next_open_size_B_limit, determine_next_open_size_Q_limit, calculate_open_limit_sell_compounding_amt_B, calculate_open_limit_buy_compounding_amt_Q
from repeating_cycle_utils import upper_bb, lower_bb, long_term_ma24, current_rsi, calculate_rsi, determine_next_open_sell_order_price_with_retry, place_next_opening_cycle_sell_order, determine_next_open_buy_order_price_with_retry, place_next_opening_cycle_buy_order, place_next_closing_cycle_buy_order, place_next_closing_cycle_sell_order

# Define locks
sell_buy_cycle_start_lock = threading.Lock()
buy_sell_cycle_start_lock = threading.Lock()
print_lock = threading.Lock()
thread_lock = threading.Lock()

# Define necessary parameters
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]
product_id = user_config["product_id"]
starting_size_B = user_config["starting_size_B"]
starting_size_Q = user_config["starting_size_Q"]
profit_percent = user_config["profit_percent"]
taker_fee = user_config["taker_fee"]
maker_fee = user_config["maker_fee"]
wait_period_unit = user_config["wait_period_unit"]
first_order_wait_period = user_config["first_order_wait_period"]
chart_interval = user_config["chart_interval"]
num_intervals = user_config["num_intervals"]
window_size = user_config["window_size"]
compound_percent = user_config["compound_percent"]
compounding_option = user_config["compounding_option"]
stacking = user_config["stacking"]
step_price = user_config["step_price"]

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
print("Fetching initial indicator stats...")


# Get the latest close price ("last") from the historical data
current_price = closing_prices[0]
app_logger.info("Current Price: %s", current_price)

# Determine 24 hour mean
print("Determining 24 hour mean...")
mean24 = determine_mean24()

# Retrieve Bollinger bands and long term 24 hr moving average calculations
print("Retrieving bollinger bands and long-term 24 hr moving average...")
app_logger.info("Upper Bollinger Band: %s", upper_bb)
app_logger.info("Lower Bollinger Band: %s", lower_bb)
app_logger.info("Long Term 24 hr Moving Average: %s", long_term_ma24)

# Print statement to indicate import of RSI calculation
print("Retrieving current RSI...")
app_logger.info("Current RSI: %s", current_rsi)

# Define order processing parameters dictionary with initialized values
order_processing_params = {
    "total_received_Q_ols": None,
    "total_spent_B_ols": None,
    "residual_amt_B_ols": None,
    "total_received_B_olb": None,
    "total_spent_Q_olb": None,
    "residual_amt_Q_olb": None,
    "total_received_B_clb": None,
    "total_spent_Q_clb": None,
    "residual_amt_Q_clb": None,
    "total_received_Q_cls": None,
    "total_spent_B_cls": None,
    "residual_amt_B_cls": None,
    "total_received_Q_oms": None,
    "total_spent_B_oms": None,
    "residual_amt_B_oms": None,
    "total_received_B_omb": None,
    "total_spent_Q_omb": None,
    "residual_amt_Q_omb": None,
    "total_received_B_cmb": None,
    "total_spent_Q_cmb": None,
    "residual_amt_Q_cmb": None,
    "total_received_Q_cms": None,
    "total_spent_B_cms": None,
    "residual_amt_B_cms": None
}

class CycleSet:

    # Class attribute to store the count of instances
    sell_buy_counter = 0
    buy_sell_counter = 0
    sell_buy_cycle_count = 0
    buy_sell_cycle_count = 0

    # Class attribute to store all created cycle set instances
    cycleset_instances = []
    
    def __init__(
            self, 
            product_id,
            starting_size,
            profit_percent,
            taker_fee,
            maker_fee,
            compound_percent,
            compounding_option,
            wait_period_unit,
            first_order_wait_period,
            chart_interval,
            num_intervals,
            window_size,
            stacking=False,
            step_price=False,
            cycle_type='',
            starting_dollar_value=None,
            current_dollar_value=None,
            percent_gain_loss_dollar=None,
            percent_gain_loss_base=None,
            percent_gain_loss_quote=None,
            average_profit_percent_per_hour=None,
            average_profit_percent_per_day=None,
            completed_cycles=0
        ):  

        self.cycle_type = cycle_type

        with print_lock:
      
            app_logger.info(f"Creating CycleSet with cycle_type: {self.cycle_type}")

            # Initialize cycle set counts for sell_buy and buy_sell
            if cycle_type == "sell_buy":
                self.cycleset_number = CycleSet.sell_buy_counter + 1
            elif cycle_type == "buy_sell":
                self.cycleset_number = CycleSet.buy_sell_counter + 1

            app_logger.info(f"CycleSet {self.cycleset_number} ({self.cycle_type}) counted")

            # Initialize cycle counts for sell_buy and buy_sell
            if cycle_type == 'sell_buy':
                CycleSet.sell_buy_cycle_count = 0  # Reset to '0' for a new CycleSet instance
                self.cycle_number = CycleSet.sell_buy_cycle_count + 1
            elif cycle_type == 'buy_sell':
                CycleSet.buy_sell_cycle_count = 0  # Reset to '0' for a new CycleSet instance
                self.cycle_number = CycleSet.buy_sell_cycle_count + 1

            app_logger.info(f"Cycle {self.cycle_number} ({self.cycle_type}) counted")

        self.cycleset_instance_id = f"CycleSet {self.cycleset_number} ({self.cycle_type})"
        self.product_id = product_id
        self.starting_size = starting_size
        self.profit_percent = profit_percent
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee
        self.compound_percent = compound_percent
        self.compounding_option = compounding_option
        self.wait_period_unit = wait_period_unit
        self.first_order_wait_period = first_order_wait_period
        self.chart_interval = chart_interval
        self.num_intervals = num_intervals
        self.window_size = window_size
        self.stacking = stacking
        self.step_price = step_price
        self.orders = []  # List to store cycle set order IDs
        self.cycle_instances = []  # Initialize an empty list to store cycle instances within a cycle set
        self.cycleset_running = False # States whether a cycle set is running or not
        self.cycleset_status = "Pending" # Describes the status as either: "Pending", "Active", "Failed", or "Stopped"
        self.completed_cycles = completed_cycles
        self.open_size_B = 0
        self.open_size_B_history = []  # Dictionary to store opening cycle sizes of base currency for each cycle
        self.open_size_Q = 0
        self.open_size_Q_history = []  # Dictionary to store opening cycle sizes of quote currency for each cycle
        self.residual_amt_B_list = [] # Dictionary to store residual amounts of base currency not used in sell orders
        self.residual_amt_Q_list = [] # Dictionary to store residual amounts of quote currency not used in buy orders
        self.sell_buy_cycleset_lock = threading.Lock()
        self.buy_sell_cycleset_lock = threading.Lock()
        self.starting_dollar_value = starting_dollar_value
        self.current_dollar_value = current_dollar_value
        self.percent_gain_loss_dollar = percent_gain_loss_dollar
        self.percent_gain_loss_base = percent_gain_loss_base
        self.percent_gain_loss_quote = percent_gain_loss_quote
        self.average_profit_percent_per_hour = average_profit_percent_per_hour
        self.average_profit_percent_per_day = average_profit_percent_per_day
 
    # Other methods...
        
    def add_cycle(self, open_size, cycle_type):
        # Assuming other attributes like product_id, open_size_Q, etc., are set in the CycleSet instance
        if cycle_type == 'sell_buy':
            CycleSet.sell_buy_cycle_count += 1
            self.cycle_number = CycleSet.sell_buy_cycle_count
        elif cycle_type == 'buy_sell':
            CycleSet.buy_sell_cycle_count += 1
            self.cycle_number = CycleSet.buy_sell_cycle_count

        cycle_instance = Cycle(
            open_size, cycleset_instance_id=self.cycleset_instance_id, cycle_type=cycle_type
        )
        self.cycle_instances.append(cycle_instance)

        return cycle_instance, self.cycle_number

    def place_starting_sell_buy_cycle_orders(self, starting_size_B, sell_buy_cycle_instance):
        try:
            from repeating_cycle_utils import product_stats, upper_bb, lower_bb, long_term_ma24, current_rsi

            starting_size_B = user_config["starting_size_B"]
            starting_size_Q = user_config["starting_size_Q"]
            
            self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Started"
            self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Pending-Starting Opening Sell Order"
            info_logger.info(self.cycle_status)

            with thread_lock:
                print("'sell_buy' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                with self.sell_buy_cycleset_lock:
                    # Determine both starting prices
                    app_logger.info("Determining starting price for sell order...")
                    starting_price_sell, starting_price_buy = determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, product_stats['quote_increment'])

                    # Use the starting_price_sell for the sell side
                    # starting_price_buy can be ignored or set to None
                        
                with self.sell_buy_cycleset_lock:   
                    # Place starting (cycle 1) opening cycle sell order
                    print("Placing the starting opening cycle sell order...")
                    open_order_id_sell = place_starting_open_sell_order(product_id, starting_size_B, starting_price_sell)
                    
                    if open_order_id_sell is not None:
                        self.orders.append(open_order_id_sell)
                        app_logger.info("Starting opening cycle sell order placed successfully: %s", open_order_id_sell)
                        self.cycle_running = True  # Set the cycle running status to True
                        self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Active"
                        self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Active-Starting Opening Sell Order"

                    if open_order_id_sell is None:
                        error_logger.error(f"Starting opening sell order not found for CycleSet {self.cycleset_number} {self.cycle_type}. Stopping the current cycle set.")
                        return
                    
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'sell_buy' thread releasing lock")
                
            with self.sell_buy_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, open_order_id_sell, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Starting opening sell order status not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Opening Sell Order"
                    print("Starting opening sell order failed. Cycle failed. Cycle set stopped.")
                    return

                # Process starting opening cycle sell order amount spent, fees, and amount to be received
                print("Processing starting opening cycle sell order assets...")
                order_processing_params = open_limit_sell_order_processing(starting_size_B, order_details, order_processing_params = {})
                total_received_Q_ols = order_processing_params["total_received_Q_ols"] 
                total_spent_B_ols = order_processing_params["total_spent_B_ols"]
                residual_amt_B_ols = order_processing_params["residual_amt_B_ols"]
                self.residual_amt_B_list.append(residual_amt_B_ols)

                try:
                    app_logger.info("Value of order_processing_params: %s", order_processing_params)
                    if order_processing_params is not None:
                        # Determine number decimal places of quote_increment (an integer)
                        decimal_places = get_decimal_places(product_stats['quote_increment'])
                        # Calculate starting (cycle 1) closing cycle buy price
                        print("Calculating starting closing cycle buy price...")
                        close_price_buy = round(starting_price_sell * (1 - profit_percent - (2 * maker_fee)), decimal_places)
                        app_logger.info("Closing cycle buy price calculated: %s", close_price_buy)
                        self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {self.cycle_number}: Pending-Starting Closing Buy Order"
                
                except Exception as e:
                    error_logger.error(f"Error in order processing: {e}")

                if order_processing_params is None:
                    # Handle the case where open_limit_sell_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for opening cycle sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {self.cycle_number}: Failed-Starting Opening Sell Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")       
                    return
                
                # Calculate starting (cycle 1) close cycle compounding amount and next starting close cycle size
                compounding_amt_Q_clb, no_compounding_Q_limit_clb = calculate_close_limit_buy_compounding_amt_Q(total_received_Q_ols, total_spent_B_ols, close_price_buy, maker_fee, product_stats["quote_increment"])
                next_size_Q = determine_next_close_size_Q_limit(compounding_option, total_received_Q_ols, no_compounding_Q_limit_clb, compounding_amt_Q_clb, compound_percent)

                if next_size_Q is not None:
                    print("Starting closing cycle compounding and next size calculated successfully")

                if next_size_Q is None:
                    error_logger.error(f"Next size could not be determined for closing buy order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'sell_buy' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Place starting closing cycle buy order
                print("Placing the starting closing cycle buy order...")
                close_order_id_buy = place_next_closing_cycle_buy_order(api_key, api_secret, product_id, next_size_Q, maker_fee, close_price_buy, product_stats)

                if close_order_id_buy is not None:
                    self.orders.append(close_order_id_buy)    
                    app_logger.info("Starting closing cycle buy order placed successfully: %s", close_order_id_buy)
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Active-Starting Closing Buy Order"
                
                if close_order_id_buy is None:
                    error_logger.error(f"Starting closing buy order not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'sell_buy' thread releasing lock")

            with self.sell_buy_cycleset_lock: 
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")   
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, close_order_id_buy, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Starting closing buy order status not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Closing Buy Order"
                    print("Starting closing buy order failed. Cycle not completed and has been stopped. Cycle set stopped.")
                    return
                
                if order_details is not None:
                    print("Starting closing cycle buy order completed successfully")

                    # Process starting closing cycle buy order amount spent, fees, and amount to be received
                    print("Processing starting closing cycle buy order assets...")
                    close_size_Q = next_size_Q
                    order_processing_params = close_limit_buy_order_processing(close_size_Q, order_details, order_processing_params = {})
                    total_received_B_clb = order_processing_params["total_received_B_clb"]
                    total_spent_Q_clb = order_processing_params["total_spent_Q_clb"]
                    residual_amt_Q_clb = order_processing_params["residual_amt_Q_clb"]
                    self.residual_amt_Q_list.append(residual_amt_Q_clb)

                if order_processing_params is not None:
                    print("Starting sell_buy cycle completed.")
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Pending-Next Opening Sell Order"

                if order_processing_params is None:
                    # Handle the case where open_limit_sell_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for closing cycle buy order for CycleSet {self.cycleset_number}. Stopping the current cycle set. Check for any open orders related to this request on exchange and handle manually.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False  # Set the cycle running status to False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Closing Buy Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")
                                       
                # Gather data for logic to determine price for next opening cycle sell order for repeating cycle

            with self.sell_buy_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Print statement to indicate current RSI calculation
                print("Calculating current RSI...")

                # Calculate current RSI
                rsi = calculate_rsi(product_id, chart_interval, length=20160)  # 15 days worth of 1-minute data
                current_rsi = rsi
                app_logger.info("Current RSI: %s", current_rsi)

                # Determine next opening cycle sell price
                print("Determining next opening cycle sell order price...")
                open_price_sell = determine_next_open_sell_order_price_with_retry(profit_percent, current_rsi, product_stats["quote_increment"], max_iterations=10)
                app_logger.info("Opening cycle sell order price determined: %s", open_price_sell)

                if open_price_sell is not None:
                    # Calculate compounding amount and size for next opening cycle sell order
                    print("Calculating compounding amount and next opening cycle sell order size...")
                    compounding_amount_B_ols, no_compounding_B_limit_ols = calculate_open_limit_sell_compounding_amt_B(total_received_B_clb, total_spent_Q_clb, open_price_sell, maker_fee, product_stats["base_increment"])
                    open_size_B = determine_next_open_size_B_limit(compounding_option, total_received_B_clb, no_compounding_B_limit_ols, compounding_amount_B_ols, compound_percent)
                    app_logger.info("open_size_B: %s", open_size_B)

                if open_price_sell is None:
                    error_logger.error(f"Failed to determine next opening cycle price for next sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                if open_size_B is not None:
                    # Append the base currency size value to the history list of the current instance
                    self.open_size_B_history.append(open_size_B)

                if open_size_B is None:
                    error_logger.error(f"Unable to determine next opening cycle sell order size for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'sell_buy' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Create a Cycle instance
                sell_buy_cycle_instance, self.cycle_number= self.add_cycle(open_size_B, "sell_buy")
                app_logger.info("sell_buy_cycle_instance: %s", sell_buy_cycle_instance )

                sell_buy_cycle_instance.cycle_number = self.cycle_number
               
                # Add the cycle instance to the list in the CycleSet and Cycle
                self.cycle_instances.append(sell_buy_cycle_instance)
                sell_buy_cycle_instance.cycle_instances.append(sell_buy_cycle_instance)

                print("Starting sell_buy cycle completed.")
                app_logger.info("Opening sell order ID: %s, Closing buy order ID: %s", open_order_id_sell, close_order_id_buy)

                # Pass the new cycle instance to the next iteraation of cycle order creation
                app_logger.info(f"Starting next sell_buy cycle, Cycle {sell_buy_cycle_instance.cycle_number} of CycleSet {self.cycleset_number} {self.cycle_type}")
                self.place_next_sell_buy_cycle_orders(open_size_B, open_price_sell, sell_buy_cycle_instance)
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'sell_buy' thread releasing lock")
                
                return open_order_id_sell, close_order_id_buy       
            
        except requests.exceptions.RequestException as e:
            # Handle request exceptions
            error_logger.error(f"An error occurred in place_starting_sell_buy_cycle_orders: {e}")
            error_logger.error(f"Status code: {e.response.status_code}" if hasattr(e, 'response') and e.response is not None else "")
            return 
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            error_logger.error(f"Error decoding JSON response in place_starting_sell_buy_cycle_orders: {e}")
            return 
        except Exception as e:
            # Handle other unexpected errors
            error_logger.error(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - An unexpected error occurred in place_starting_sell_buy_cycle_orders: {e}")
            return 

    def place_starting_buy_sell_cycle_orders(self, starting_size_Q, buy_sell_cycle_instance):
        try:
            from repeating_cycle_utils import product_stats, upper_bb, lower_bb, long_term_ma24, current_rsi

            starting_size_B = user_config["starting_size_B"]
            starting_size_Q = user_config["starting_size_Q"]

            self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Started"
            self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Pending-Starting Opening Buy Order"
            info_logger.info(self.cycle_status)

            with thread_lock:
                print("'buy_sell' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                with self.buy_sell_cycleset_lock:
                        # Determine both starting prices
                        app_logger.info("Determining starting price for buy order...")
                        starting_price_sell, starting_price_buy = determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, product_stats['quote_increment'])

                    # Use the starting_price_buy for the buy side
                    # starting_price_sell can be ignored or set to None
                        
                with self.buy_sell_cycleset_lock:
                    # Place starting (cycle 1) opening cycle buy order
                    print("Placing the starting opening cycle buy order...")
                    open_order_id_buy = place_starting_open_buy_order(product_id, product_stats, starting_size_Q, starting_price_buy, maker_fee)
                    
                    if open_order_id_buy is not None:
                        self.orders.append(open_order_id_buy)
                        app_logger.info("Starting opening cycle buy order placed successfully: %s", open_order_id_buy)
                        self.cycle_running = True  # Set the cycle running status to True
                        self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Active"
                        self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Active-Starting Opening Buy Order"

                    if open_order_id_buy is None:
                        error_logger.error(f"Starting opening buy order not found for CycleSet {self.cycleset_number} {self.cycle_type}. Stopping the current cycle set.")
                        return
                    
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'buy_sell' thread releasing lock")
                    
            with self.buy_sell_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")    
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, open_order_id_buy, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Starting opening buy order status not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Opening Buy Order"
                    print("Starting opening buy order failed. Cycle failed. Cycle set stopped.")
                    return            

                # Process starting opening cycle buy order amount spent, fees, and amount to be received
                print("Processing starting opening cycle buy order assets...")
                order_processing_params = open_limit_buy_order_processing(starting_size_Q, order_details, order_processing_params = {})
                total_received_B_olb = order_processing_params["total_received_B_olb"] 
                total_spent_Q_olb = order_processing_params["total_spent_Q_olb"]
                residual_amt_Q_olb = order_processing_params["residual_amt_Q_olb"]
                self.residual_amt_Q_list.append(residual_amt_Q_olb)

                try:
                    app_logger.info("Value of order_processing_params: %s", order_processing_params)
                    if order_processing_params is not None:
                        # Determine number decimal places of quote_increment (an integer)
                        decimal_places = get_decimal_places(product_stats['quote_increment'])
                        # Calculate starting (cycle 1) closing cycle buy price
                        print("Calculating starting closing cycle sell price...")
                        close_price_sell = round(starting_price_buy * (1 + profit_percent + (2 * maker_fee)), decimal_places)
                        app_logger.info("Closing cycle sell price calculated: %s", close_price_sell)
                        self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Pending-Starting Closing Sell Order"
                
                except Exception as e:
                    error_logger.error(f"Error in order processing: {e}")
                    return

                if order_processing_params is None:
                    # Handle the case where open_limit_buy_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for cycle set {self.cycleset_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Opening Buy Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")
                    return 
                
                # Calculate starting (cycle 1) closing cycle compounding amount and next starting closing cycle size
                compounding_amt_B_cls, no_compounding_B_limit_cls = calculate_close_limit_sell_compounding_amt_B(total_received_B_olb, total_spent_Q_olb, close_price_sell, maker_fee, product_stats["base_increment"])
                next_size_B = determine_next_close_size_B_limit(compounding_option, total_received_B_olb, no_compounding_B_limit_cls, compounding_amt_B_cls, compound_percent)

                if next_size_B is not None:
                    print("Starting closing cycle compounding and next size calculated successfully")

                if next_size_B is None:
                    error_logger.error(f"Next size could not be determined for closing sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")
                
            with thread_lock:
                print("'buy_sell' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Place starting closing cycle sell order
                print("Placing the starting closing cycle sell order...")
                close_order_id_sell = place_next_closing_cycle_sell_order(api_key, api_secret, product_id, next_size_B, close_price_sell)
                    
                if close_order_id_sell is not None:
                    self.orders.append(close_order_id_sell)    
                    app_logger.info("Starting closing cycle sell order placed successfully: %s", close_order_id_sell)
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Active-Starting Closing Sell Order"

                if close_order_id_sell is None:
                    error_logger.error(f"Starting closing sell order not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'buy_sell' thread releasing lock")
                    
            with self.buy_sell_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")    
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, close_order_id_sell, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Starting closing sell order status not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Closing Sell Order"
                    print("Starting closing sell order failed. Cycle not completed and has been stopped. Cycle set stopped.")
                    return
                
                if order_details is not None:
                    print("Starting closing cycle sell order completed successfully")

                    # Process starting closing cycle sell order amount spent, fees, and amount to be received
                    print("Processing starting closing cycle sell order assets...")
                    close_size_B = next_size_B
                    order_processing_params = close_limit_sell_order_processing(close_size_B, order_details, order_processing_params = {})
                    total_received_Q_cls = order_processing_params["total_received_Q_cls"]
                    total_spent_B_cls = order_processing_params["total_spent_B_cls"]
                    residual_amt_B_cls = order_processing_params["residual_amt_B_cls"]
                    self.residual_amt_B_list.append(residual_amt_B_cls)

                if order_processing_params is not None:
                    print("Starting buy_sell cycle completed.")
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Completed-Pending-Next Opening Buy Order"

                if order_processing_params is None:
                    # Handle the case where open_limit_buy_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for closing cycle sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set. Check for any open orders related to this request on exchange and handle manually.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False  # Set the cycle running status to False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} {self.cycle_type} Cycle {self.cycle_number}: Failed-Starting Closing Sell Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")
                    return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

                # Gather data for logic to determine price for next opening cycle sell order for repeating cycle
                    
            with self.buy_sell_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Print statement to indicate current RSI calculation
                print("Calculating current RSI...")

                # Calculate current RSI
                rsi = calculate_rsi(product_id, chart_interval, length=20160)  # 15 days worth of 1-minute data
                current_rsi = rsi
                app_logger.info("Current RSI: %s", current_rsi)

                # Determine next opening cycle sell price
                print("Determining next opening cycle buy order price...")
                open_price_buy = determine_next_open_buy_order_price_with_retry(profit_percent, current_rsi, product_stats["quote_increment"], max_iterations=10)
                app_logger.info("Opening cycle buy order price determined: %s", open_price_buy)

                if open_price_buy is not None:
                    # Calculate compounding amount and size for next opening cycle buy order
                    print("Calculating compounding amount and next opening cycle buy order size...")
                    compounding_amount_Q_olb, no_compounding_Q_limit_olb = calculate_open_limit_buy_compounding_amt_Q(total_received_Q_cls, total_spent_B_cls, open_price_buy, maker_fee, product_stats["quote_increment"])
                    open_size_Q = determine_next_open_size_Q_limit(compounding_option, total_received_Q_cls, no_compounding_Q_limit_olb, compounding_amount_Q_olb, compound_percent)
                    app_logger.info("open_size_Q: %s", open_size_Q)

                if open_price_buy is None:
                    error_logger.error(f"Failed to determine opening cycle price for next buy order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                if open_size_Q is not None:
                    # Append the quote currency size value to the history list of the current instance
                    self.open_size_Q_history.append(open_size_Q)

                if open_size_Q is None:
                    error_logger.error(f"Unable to determine next opening cycle buy order size for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'buy_sell' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Create a Cycle instance
                buy_sell_cycle_instance, self.cycle_number = self.add_cycle(open_size_Q, "buy_sell")
                app_logger.info("buy_sell_cycle_instance: %s", buy_sell_cycle_instance)

                buy_sell_cycle_instance.cycle_number = self.cycle_number
               
                # Add the cycle instance to the list in the CycleSet and Cycle
                self.cycle_instances.append(buy_sell_cycle_instance)
                buy_sell_cycle_instance.cycle_instances.append(buy_sell_cycle_instance)

                print("Starting buy_sell cycle completed.")
                app_logger.info("Opening buy order ID: %s, Closing sell order ID: %s", open_order_id_buy, close_order_id_sell)

                # Pass the new cycle instance to the next iteraation of cycle order creation
                app_logger.info(f"Starting next buy_sell cycle, Cycle {buy_sell_cycle_instance.cycle_number} of CycleSet {self.cycleset_number} {self.cycle_type}")
                self.place_next_buy_sell_cycle_orders(open_size_Q, open_price_buy, buy_sell_cycle_instance)
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'buy_sell' thread releasing lock")
               
                return open_order_id_buy, close_order_id_sell
        
        except requests.exceptions.RequestException as e:
            # Handle request exceptions
            error_logger.error(f"An error occurred in place_starting_buy_sell_cycle_orders: {e}")
            error_logger.error(f"Status code: {e.response.status_code}" if hasattr(e, 'response') and e.response is not None else "")
            return 
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            error_logger.error(f"Error decoding JSON response in place_starting_buy_sell_cycle_orders: {e}")
            return 
        except Exception as e:
            # Handle other unexpected errors
            error_logger.error(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - An unexpected error occurred in place_starting_buy_sell_cycle_orders: {e}")
            return  
    
    def start_sell_buy_starting_cycle(self, user_config, sell_buy_cycle_set_counter):
        with sell_buy_cycle_start_lock:
            # Check if there is new user input
            if user_config:
                with print_lock:
                    app_logger.info(f"Cycle Set {sell_buy_cycle_set_counter} (sell_buy) starting cycle initiated...")

                # Call the add_cycle() function to create the Cycle instance
                sell_buy_cycle_instance, self.cycle_number = self.add_cycle(open_size=user_config["starting_size_B"], cycle_type="sell_buy")
            
                # Place starting orders for 'sell-buy' cycle and get order IDs
                sell_buy_order_ids = self.place_starting_sell_buy_cycle_orders(user_config["starting_size_B"], sell_buy_cycle_instance)

                return sell_buy_cycle_instance, sell_buy_order_ids
            else:
                error_logger.error("Invalid user configuration. CycleSet and Cycle not started.")

    def start_buy_sell_starting_cycle(self, user_config, buy_sell_cycle_set_counter):
        with buy_sell_cycle_start_lock:
            # Check if there is new user input
            if user_config:
                with print_lock:
                    app_logger.info(f"Cycle Set {buy_sell_cycle_set_counter} (buy_sell) starting cycle initiated...")

                # Call the add_cycle() function to create the Cycle instance
                buy_sell_cycle_instance, self.cycle_number = self.add_cycle(open_size=user_config["starting_size_Q"], cycle_type="buy_sell")

                # Place starting orders for 'sell-buy' cycle and get order IDs
                buy_sell_order_ids = self.place_starting_buy_sell_cycle_orders(user_config["starting_size_Q"], buy_sell_cycle_instance)

                return buy_sell_cycle_instance, buy_sell_order_ids
            else:
                error_logger.error("Invalid user configuration. CycleSet and Cycle not started.")

    def get_open_orders(self):
        open_orders = [order for order in self.orders if get_order_status(order) == 'OPEN']
        return open_orders
    
    def cancel_open_orders(self, orders_to_cancel):
        cancel_results = cancel_orders(orders_to_cancel)
        return cancel_results
    
    def stop(self):
        with print_lock:
            # Access the last cycle in the set
            if self.cycle_instances:
                last_cycle = self.cycle_instances[-1]
            
                # Get the open orders in the last cycle
                open_orders = last_cycle.get_open_orders()

                if open_orders:
                    # Initiate cancel requests for open orders
                    cancel_results = self.cancel_open_orders(open_orders)  # Use your cancel_orders function
                    if cancel_results:
                        print("Cancel requests initiated successfully.")
                    else:
                        print("Failed to initiate cancel requests.")
            
            self.running = False  # This flag prevents further cycling

    def cycleset_is_running(self):
        return self.cycleset_running
    
    def get_status(self):
        with thread_lock:
            if not self.cycle_instances:
                info_logger.info(f"Cycle Set {self.cycleset_number} ({self.cycle_type}) has no completed cycles yet.")
                return
            
            last_cycle = self.cycle_instances[-1]
            
            status_info = [
                f"Cycle Set {self.cycleset_number} ({self.cycle_type}) status: {self.cycleset_status}",
                f"Completed cycles: {last_cycle}",
                f"Cycle {self.cycle_number} status: {self.cycle_status}",
            ]

            info_logger.info("Status info: %s", status_info)
            
            open_orders = last_cycle.get_open_orders()
            if open_orders:
                status_info.append("Current open order:")
                for order in open_orders:
                    status_info.append(f"  - Order ID: {order.order_id}")
                    status_info.append(f"    Order Status: {order.status}")
                    status_info.append(f"    Order Details: {order.details}")
            
            # Join all status information
            status_message = "\n".join(status_info)
            
            info_logger.info("Status message: %s", status_message)

    def get_cycleset_data(self):
        # Calculate and return a dictionary of relevant data
    
        cycleset_data = {
            'cycle_set_number': self.cycleset_number,
            'cycleset_instance_id': self.cycleset_instance_id,
            'product_id': self.product_id,
            'starting_size': self.starting_size,
            'profit_percent': self.profit_percent,
            'taker_fee': self.taker_fee,
            'maker_fee': self.maker_fee,
            'compound_percent': self.compound_percent,
            'compounding_option': self.compounding_option,
            'wait_period_unit': self.wait_period_unit,
            'first_order_wait_period': self.first_order_wait_period,
            'chart_interval': self.chart_interval,
            'num_intervals': self.num_intervals,
            'window_size': self.window_size,
            'stacking': self.stacking,
            'step_price': self.step_price,
            'cycle_type': self.cycle_type,
            'orders': self.orders,
            'cycle_instances': self.cycle_instances,
            'cycle_set_running': self.cycleset_running,
            'cycleset_status': self.cycleset_status,
            'completed_cycles': self.completed_cycles,
            'starting_dollar_value': self.starting_dollar_value,
            'current_dollar_value': self.current_dollar_value,
            'percent_gain_loss_dollar': self.percent_gain_loss_dollar,
            'percent_gain_loss_base': self.percent_gain_loss_base,
            'percent_gain_loss_quote': self.percent_gain_loss_quote,
            'average_profit_percent_per_hour': self.average_profit_percent_per_hour,
            'average_profit_percent_per_day': self.average_profit_percent_per_day
            # ... other data
        }
    
        info_logger.info("Cycle set data: %s", cycleset_data)
        return cycleset_data
    
    def place_next_sell_buy_cycle_orders(self, open_size_B, open_price_sell, sell_buy_cycle_instance):
        try:
            from repeating_cycle_utils import closing_prices, product_stats, upper_bb, long_term_ma24, current_rsi

            # Update 'cycle_number' in the CycleSet class
            self.cycle_number = sell_buy_cycle_instance.cycle_number

            with thread_lock:
                print("'sell_buy' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                with self.sell_buy_cycleset_lock:
                    # Place next opening cycle sell order
                    print("Placing the next opening cycle sell order...")
                    open_order_id_sell = place_next_opening_cycle_sell_order(api_key, api_secret, product_id, open_size_B, open_price_sell)
                    
                    if open_order_id_sell is not None:
                        self.orders.append(open_order_id_sell)
                        app_logger.info("Opening cycle sell order placed successfully: %s", open_order_id_sell)
                        self.cycle_running = True  # Set the cycle running status to True
                        self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Active-Opening Cycle Sell Order"
                        print(self.cycle_status)

                    if open_order_id_sell is None:
                        error_logger.error(f"Opening cycle sell order not found for CycleSet {self.cycleset_number} {self.cycle_type}. Stopping the current cycle set.")
                        return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'sell_buy' thread releasing lock")

            with self.sell_buy_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, open_order_id_sell, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Opening sell order status not found for CycleSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Failed-Opening Cycle Sell Order"
                    print("Opening sell order failed. Cycle failed. Cycle set stopped.")
                    return

                # Process opening cycle sell order amount spent, fees, and amount to be received
                print("Processing opening cycle sell order assets...")
                order_processing_params = open_limit_sell_order_processing(open_size_B, order_details, order_processing_params = {})
                total_received_Q_ols = order_processing_params["total_received_Q_ols"] 
                total_spent_B_ols = order_processing_params["total_spent_B_ols"]
                residual_amt_B_ols = order_processing_params["residual_amt_B_ols"]
                self.residual_amt_B_list.append(residual_amt_B_ols)

                try:
                    app_logger.info("Value of order_processing_params: %s", order_processing_params)
                    if order_processing_params is not None:
                        # Determine number decimal places of quote_increment (an integer)
                        decimal_places = get_decimal_places(product_stats['quote_increment'])
                        # Calculate closing cycle buy price
                        print("Calculating closing cycle buy price...")
                        close_price_buy = round(open_price_sell * (1 - profit_percent - (2 * maker_fee)), decimal_places)
                        app_logger.info("Closing cycle buy price calculated: %s", close_price_buy)
                        self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Pending-Closing Buy Order"
                
                except Exception as e:
                        error_logger.error(f"Error in order processing: {e}")

                if order_processing_params is None:
                    # Handle the case where open_limit_sell_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for opening cycle sell order for CycleSet {self.cycleset_number}({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = "Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Failed-Opening Sell Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")       
                    return
                
                # Calculate starting (cycle 1) close cycle compounding amount and next starting close cycle size
                compounding_amt_Q_clb, no_compounding_Q_limit_clb = calculate_close_limit_buy_compounding_amt_Q(total_received_Q_ols, total_spent_B_ols, close_price_buy, maker_fee, product_stats["quote_increment"])
                close_size_Q = determine_next_close_size_Q_limit(compounding_option, total_received_Q_ols, no_compounding_Q_limit_clb, compounding_amt_Q_clb, compound_percent)

                if close_size_Q is not None:
                    print("Closing cycle compounding and next size calculated successfully")

                if close_size_Q is None:
                    error_logger.error(f"Closing cycle size could not be determined for closing buy order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'sell_buy' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Place closing cycle buy order
                print("Placing the closing cycle buy order...")
                close_order_id_buy = place_next_closing_cycle_buy_order(api_key, api_secret, product_id, close_size_Q, maker_fee, close_price_buy, product_stats)

                if close_order_id_buy is not None:
                    self.orders.append(close_order_id_buy)    
                    app_logger.info("Closing cycle buy order placed successfully: %s", close_order_id_buy)
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Active-Closing Buy Order"
                
                if close_order_id_buy is None:
                    error_logger.error(f"Closing buy order not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
            
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'sell_buy' thread releasing lock")

            with self.sell_buy_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, close_order_id_buy, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Closing buy order status not found for CycleSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Failed-Closing Buy Order"
                    print("Closing buy order failed. Cycle not completed and has been stopped. Cycle set stopped.")
                    return

                if order_details is not None:
                    print("Closing cycle buy order completed successfully")
            
                    # Process closing cycle buy order amount spent, fees, and amount to be received
                    print("Processing closing cycle buy order assets...")
                    order_processing_params = close_limit_buy_order_processing(close_size_Q, order_details, order_processing_params = {})
                    total_received_B_clb = order_processing_params["total_received_B_clb"]
                    total_spent_Q_clb = order_processing_params["total_spent_Q_clb"]
                    residual_amt_Q_clb = order_processing_params["residual_amt_Q_clb"]
                    self.residual_amt_Q_list.append(residual_amt_Q_clb)

                if order_processing_params is not None:
                    app_logger.info(f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle{sell_buy_cycle_instance.cycle_number} completed.")
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Completed-Pending Next Opening Sell Order"

                if order_processing_params is None:
                    # Handle the case where close_limit_buy_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for closing cycle buy order for CycleSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}. Stopping the current cycle set. Check for any open orders related to this request on exchange and handle manually.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False  # Set the cycle running status to False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {sell_buy_cycle_instance.cycle_number}: Failed-Closing Buy Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

                # Gather data for logic to determine price for next opening cycle sell order for repeating cycle

            with self.sell_buy_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Print statement to indicate current RSI calculation
                print("Calculating current RSI...")

                # Calculate current RSI
                rsi = calculate_rsi(product_id, chart_interval, length=20160)  # 15 days worth of 1-minute data
                current_rsi = rsi
                app_logger.info("Current RSI: %s", current_rsi)

                
                # Determine next opening cycle sell price
                print("Determining next opening cycle sell order price...")
                open_price_sell = determine_next_open_sell_order_price_with_retry(profit_percent, current_rsi, product_stats["quote_increment"], max_iterations=10)
                app_logger.info("Opening cycle sell order price determined: %s", open_price_sell)

                if open_price_sell is not None:
                    # Calculate compounding amount and size for next opening cycle sell order
                    print("Calculating compounding amount and next opening cycle sell order size...")
                    compounding_amount_B_ols, no_compounding_B_limit_ols = calculate_open_limit_sell_compounding_amt_B(total_received_B_clb, total_spent_Q_clb, open_price_sell, maker_fee, product_stats["base_increment"])
                    open_size_B = determine_next_open_size_B_limit(compounding_option, total_received_B_clb, no_compounding_B_limit_ols, compounding_amount_B_ols, compound_percent)
                
                if open_price_sell is None:
                    error_logger.error(f"Failed to determine next opening cycle price for next sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                if open_size_B is not None:
                    # Append the base currency size value to the history list of the current instance
                    self.open_size_B_history.append(open_size_B)

                if open_size_B is None:
                    error_logger.error(f"Opening cycle size could not be determined for openining sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'sell_buy' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Create a new Cycle instance
                sell_buy_cycle_instance, self.cycle_number = self.add_cycle(open_size_B, "sell_buy")

                sell_buy_cycle_instance.cycle_number = self.cycle_number
                
                # Add the cycle instance to the list in the CycleSet and Cycle
                self.cycle_instances.append(sell_buy_cycle_instance)
                sell_buy_cycle_instance.cycle_instances.append(sell_buy_cycle_instance)

                print("Sell_buy cycle completed.")
                app_logger.info("Opening sell order ID: %s, Closing buy order ID: %s", open_order_id_sell, close_order_id_buy)

                # Call methods on the Cycle instance
                app_logger.info(f"Starting next sell_buy cycle, Cycle {sell_buy_cycle_instance.cycle_number} of CycleSet {self.cycleset_number} ({self.cycle_type})")
                self.place_next_sell_buy_cycle_orders(open_size_B, open_price_sell, sell_buy_cycle_instance)
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'sell_buy' thread releasing lock")

                return open_order_id_sell, close_order_id_buy
        
        except requests.exceptions.RequestException as e:
            # Handle request exceptions
            error_logger.error(f"An error occurred in place_next_sell_buy_cycle_orders: {e}")
            error_logger.error(f"Status code: {e.response.status_code}" if hasattr(e, 'response') and e.response is not None else "")
            return 
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            error_logger.error(f"Error decoding JSON response in place_next_sell_buy_cycle_orders: {e}")
            return 
        except Exception as e:
            # Handle other unexpected errors
            error_logger.error(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - An unexpected error occurred in place_next_sell_buy_cycle_orders: {e}")
            return  
        
    def place_next_buy_sell_cycle_orders(self, open_size_Q, open_price_buy, buy_sell_cycle_instance):
        try:
            from repeating_cycle_utils import closing_prices, product_stats, lower_bb, long_term_ma24, current_rsi

            # Update 'cycle_number' in the CycleSet class
            self.cycle_number = buy_sell_cycle_instance.cycle_number

            with thread_lock:
                print("'buy_sell' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                with self.buy_sell_cycleset_lock:
                    # Place next opening cycle buy order
                    print("Placing the next opening cycle buy order...")
                    open_order_id_buy = place_next_opening_cycle_buy_order(api_key, api_secret, product_id, open_size_Q, maker_fee, open_price_buy, product_stats)
                    
                    if open_order_id_buy is not None:
                        self.orders.append(open_order_id_buy)
                        app_logger.info("Opening cycle buy order placed successfully: %s", open_order_id_buy)
                        self.cycle_running = True  # Set the cycle running status to True
                        self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Active-Opening Cycle Buy Order"
                        print (self.cycle_status)

                    if open_order_id_buy is None:
                        error_logger.error(f"Opening buy order not found for CycleSet {self.cycleset_number} {self.cycle_type}. Stopping the current cycle set.")
                        return
                    
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'buy_sell' thread releasing lock")

            with self.buy_sell_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, open_order_id_buy,max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Opening buy order status not found for CycleSet {self.cycleset_number}({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Failed-Opening Cycle Buy Order"
                    print("Opening buy order failed. Cycle failed. Cycle set stopped.")
                    return

                # Process opening cycle buy order amount spent, fees, and amount to be received
                print("Processing opening cycle buy order assets...")
                order_processing_params = open_limit_buy_order_processing(open_size_Q, order_details, order_processing_params = {})
                total_received_B_olb = order_processing_params["total_received_B_olb"] 
                total_spent_Q_olb = order_processing_params["total_spent_Q_olb"]
                residual_amt_Q_olb = order_processing_params["residual_amt_Q_olb"]
                self.residual_amt_Q_list.append(residual_amt_Q_olb)

                try:
                    app_logger.info("Value of order_processing_params: %s", order_processing_params)
                    if order_processing_params is not None:
                        # Determine number decimal places of quote_increment (an integer)
                        decimal_places = get_decimal_places(product_stats['quote_increment'])
                        # Calculate closing cycle buy price
                        print("Calculating closing cycle sell price...")
                        close_price_sell = round(open_price_buy * (1 + profit_percent + (2 * maker_fee)), decimal_places)
                        app_logger.info("Closing cycle sell price calculated: %s", close_price_sell)
                        self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Pending-Closing Sell Order"
                
                except Exception as e:
                        error_logger.error(f"Error in order processing: {e}")

                if order_processing_params is None:
                    # Handle the case where open_limit_buy_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for opening cycle buy order for CycleSet {self.cycleset_number}({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycleset_status = "Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Failed-Opening Buy Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")       
                    return
                
                # Calculate closing cycle compounding amount and closing cycle size
                compounding_amt_B_cls, no_compounding_B_limit_cls = calculate_close_limit_sell_compounding_amt_B(total_received_B_olb, total_spent_Q_olb, close_price_sell, maker_fee, product_stats["base_increment"])
                close_size_B = determine_next_close_size_B_limit(compounding_option, total_received_B_olb, no_compounding_B_limit_cls, compounding_amt_B_cls, compound_percent)

                if close_size_B is not None:
                    print("Closing cycle compounding and next size calculated successfully")

                if close_size_B is None:
                    error_logger.error(f"Closing cycle size could not be determined for closing sell order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'buy_sell' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")
                # Place closing cycle sell order
                print("Placing the closing cycle sell order...")
                close_order_id_sell = place_next_closing_cycle_sell_order(api_key, api_secret, product_id, close_size_B, close_price_sell)

                if close_order_id_sell is not None:
                    self.orders.append(close_order_id_sell)    
                    app_logger.info("Closing cycle sell order placed successfully: %s", close_order_id_sell)
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Active-Closing Sell Order"
                
                if close_order_id_sell is None:
                    error_logger.error(f"Closing sell order not found for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return

                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'buy_sell' thread releasing lock")

            with self.buy_sell_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Call wait_for_order function
                order_details = wait_for_order(api_key, api_secret, close_order_id_sell, max_retries=3)

                # Check if the order_details is None
                if order_details is None:
                    # Handle the case where wait_for_order did not complete successfully
                    error_logger.error(f"Closing sell order status not found for CycleSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}. Stopping the current cycle set.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type})Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Failed-Closing Sell Order"
                    print("Closing sell order failed. Cycle not completed and has been stopped. Cycle set stopped.")
                    return

                if order_details is not None:
                    print("Closing cycle sell order completed successfully")
            
                    # Process closing cycle sell order amount spent, fees, and amount to be received
                    print("Processing closing cycle sell order assets...")
                    order_processing_params = close_limit_sell_order_processing(close_size_B, order_details, order_processing_params = {})
                    total_received_Q_cls = order_processing_params["total_received_Q_cls"]
                    total_spent_B_cls = order_processing_params["total_spent_B_cls"]
                    residual_amt_B_cls = order_processing_params["residual_amt_B_cls"]
                    self.residual_amt_B_list.append(residual_amt_B_cls)

                if order_processing_params is not None:
                    app_logger.info(f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle{buy_sell_cycle_instance.cycle_number} completed.")
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Completed-Pending Next Opening Buy Order"

                if order_processing_params is None:
                    # Handle the case where close_limit_sell_order_processing did not complete successfully
                    error_logger.error(f"Order processing parameters not found for closing cycle sell order for CycleSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}. Stopping the current cycle set. Check for any open orders related to this request on exchange and handle manually.")
                    self.cycleset_running = False # Set cycle set attribute to not running
                    self.cycle_running = False  # Set the cycle running status to False
                    self.cycleset_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Failed"
                    self.cycle_status = f"CyclSet {self.cycleset_number} ({self.cycle_type}) Cycle {buy_sell_cycle_instance.cycle_number}: Failed-Closing Sell Order"
                    print("Order processing failed. Cycle not completed. Cycle set stopped. Check for any open orders related to this request on exchange and handle manually.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")
            
                # Gather data for logic to determine price for next opening cycle buy order for repeating cycle

            with self.buy_sell_cycleset_lock:
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Before important step")
                # Print statement to indicate current RSI calculation
                print("Calculating current RSI...")

                # Calculate current RSI
                rsi = calculate_rsi(product_id, chart_interval, length=20160)  # 15 days worth of 1-minute data
                current_rsi = rsi
                app_logger.info("Current RSI: %s", current_rsi)

                
                # Determine next opening cycle buy price
                print("Determining next opening cycle buy order price...")
                open_price_buy = determine_next_open_buy_order_price_with_retry(profit_percent, current_rsi,product_stats["quote_increment"], max_iterations=10)
                app_logger.info("Opening cycle buy order price determined: %s", open_price_buy)

                if open_price_buy is not None:
                    # Calculate compounding amount and size for next opening cycle buy order
                    print("Calculating compounding amount and next opening cycle buy order size...")
                    compounding_amount_Q_olb, no_compounding_Q_limit_olb = calculate_open_limit_buy_compounding_amt_Q(total_received_Q_cls, total_spent_B_cls, open_price_buy, maker_fee, product_stats["quote_increment"])
                    open_size_Q = determine_next_open_size_Q_limit(compounding_option, total_received_Q_cls, no_compounding_Q_limit_olb, compounding_amount_Q_olb, compound_percent)
                
                if open_price_buy is None:
                    error_logger.error(f"Failed to determine opening cycle price for next buy order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
            
                if open_size_Q is not None:
                    # Append the quote currency size value to the history list of the current instance
                    self.open_size_Q_history.append(open_size_Q)

                if open_size_Q is None:
                    error_logger.error(f"Opening cycle size could not be determined for opening buy order for CycleSet {self.cycleset_number}. Stopping the current cycle set.")
                    return
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - After important step")

            with thread_lock:
                print("'buy_sell' thread acquired lock")
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Acquired lock")        
                # Create a new Cycle instance
                buy_sell_cycle_instance, self.cycle_number = self.add_cycle(open_size_Q, "buy_sell")

                buy_sell_cycle_instance.cycle_number = self.cycle_number

                # Add the cycle instance to the list in the CycleSet and Cycle
                self.cycle_instances.append(buy_sell_cycle_instance)
                buy_sell_cycle_instance.cycle_instances.append(buy_sell_cycle_instance)
               
                print("Buy_sell cycle completed.")
                app_logger.info("Opening buy order ID: %s, Closing sell order ID: %s", open_order_id_buy, close_order_id_sell)
                
                # Call methods on the Cycle instance
                app_logger.info(f"Starting next buy_sell cycle, Cycle {buy_sell_cycle_instance.cycle_number} of CycleSet {self.cycleset_number}")
                self.place_next_buy_sell_cycle_orders(open_size_Q, open_price_buy, buy_sell_cycle_instance)
                
                print(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - Released lock")
                print("'buy_sell' thread releasing lock")

                return open_order_id_buy, close_order_id_sell
        
        except requests.exceptions.RequestException as e:
            # Handle request exceptions
            error_logger.error(f"An error occurred in place_next_buy_sell_cycle_orders: {e}")
            error_logger.error(f"Status code: {e.response.status_code}" if hasattr(e, 'response') and e.response is not None else "")
            return 
        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            error_logger.error(f"Error decoding JSON response in place_next_buy_sell_cycle_orders: {e}")
            return 
        except Exception as e:
            # Handle other unexpected errors
            error_logger.error(f"Thread ID: {threading.get_ident()} - Timestamp: {time.time()} - An unexpected error occurred in place_next_buy_sell_cycle_orders: {e}")
            return

class Cycle:
    # Class attribute to store the count of instances
    count = 0

    # Class attribute to store all created cycle set instances
    cycle_instances = []

    def __init__(
            self, 
            open_size,
            cycleset_instance_id,
            cycle_type
        ):

        # Initialize cycle counts for sell_buy and buy_sell
        if cycle_type == 'sell_buy':
            Cycle.sell_buy_cycle_count = 0  # Reset to '0' for a new CycleSet instance
            self.cycle_number = Cycle.sell_buy_cycle_count + 1
        elif cycle_type == 'buy_sell':
            Cycle.buy_sell_cycle_count = 0  # Reset to '0' for a new CycleSet instance
            self.cycle_number = Cycle.buy_sell_cycle_count + 1

        self.open_size = open_size 
        self.cycleset_instance_id = cycleset_instance_id 
        self.cycle_type = cycle_type
        self.cycle_instance_id = f"Cycle ({self.cycle_type}) cycle_number: {self.cycle_number}"
        self.cycle_running = False  # Initialize the cycle running attribute
        self.cycle_status = "Pending" # Can have statuses: 'Pending', 'Pending-Opening Sell Order', 'Active-Opening Sell Order', 'Pending-Closing Buy Order', 'Active-Closing Buy Order', 'Pending-Opening Buy Order', 'Active-Opening Buy Order', 'Pending-Closing Sell Order', 'Active Closing Sell Order', or 'Completed'
        self.orders = []  # Initialize as an empty list
        self.sell_buy_cycle_lock = threading.Lock()
        self.buy_sell_cycle_lock = threading.Lock()

    # Other methods...

    def check_order_status(self, order_id):
        order_data = get_order_status(order_id)
        if order_data:
            order_status = order_data.get("status")
            return order_status
        else:
            # Handle the case when the API request fails
            return "API request failed"
    def get_open_orders(self):
        open_orders = [order_id for order_id in self.orders if get_order_status(order_id) == 'OPEN']
        return open_orders
    
    def cancel_open_orders(self, open_orders):
        cancel_results = cancel_orders(open_orders)
        return cancel_results

    def cycle_is_running(self):
        # Check if a cycle is running
        for order_id in self.orders:
            order_status = get_order_status(order_id)  # Implement this function to get order status
            if order_status != "CANCELLED":
                self.cycle_running = True
            else:
                self.cycle_running = False

# Access the instance_id to identify instances
for cycleset_instance in CycleSet.cycleset_instances:
    app_logger.info(f"Cycle Set Instance ID: {cycleset_instance.instance_id}, Product ID: {cycleset_instance.product_id}, Starting Size: {cycleset_instance.starting_size}, Profit Percent: {cycleset_instance.profit_percent}, Taker Fee: {cycleset_instance.taker_fee}, Maker Fee: {cycleset_instance.maker_fee}, Compound Percent: {cycleset_instance.compound_percent}, Compounding Option: {cycleset_instance.compounding_option}, Wait Period Unit: {cycleset_instance.wait_period_unit}, First Order Wait Period: {cycleset_instance.first_order_wait_period}, Chart Intervals: {cycleset_instance.chart_intervals}, Number Intervals: {cycleset_instance.num_intervals}, Window Size: {cycleset_instance.window_size}, Stacking: {cycleset_instance.stacking}, Step Price: {cycleset_instance.step_price}, Cycle Type: {cycleset_instance.cycle_type}")

# Other functions for managing cycle-specific logic...

def determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, quote_increment):
    starting_price_sell = None
    starting_price_buy = None
    quote_increment = float(quote_increment)

    with print_lock:
        if starting_size_B > 0:
            if current_price > mean24 and starting_size_Q >=0:
                # Market is favorable for sell order
                print("Market is favorable for sell order")
                starting_price_sell = determine_starting_sell_parameters(current_price, upper_bb, starting_size_B, mean24)

                # We still calculate a buy price if quote assets are available
                if starting_price_sell is not None and starting_size_Q > 0:
                    rounded_buy_estimate = round((starting_price_sell * 0.995), -int(math.floor(math.log10(quote_increment))))

                    # Ensure the rounded price is at least quote_increment
                    if rounded_buy_estimate < quote_increment:
                        rounded_buy_estimate = quote_increment
                
                    starting_price_buy = rounded_buy_estimate
                    info_logger.info("Starting price determined for buy order: %s", starting_price_buy)
 
            if current_price < mean24:
                if starting_size_Q == 0:
                    # Market is not favorable for sell order
                    print("Market is not favorable for a sell order now")
                    print("Waiting for favorable market conditions for sell order...")
                    starting_price_sell = determine_starting_sell_parameters(current_price, upper_bb, starting_size_B, mean24)

                # If quote assets are available market is favorable for buy order
                if starting_size_Q > 0:
                    print("Market is favorable for buy order")
                    starting_price_buy = determine_starting_buy_parameters(current_price, lower_bb, starting_size_Q, mean24)

                    # Will still calculate a sell price because base assets available
                    if starting_price_buy is not None:
                        rounded_sell_estimate = round((starting_price_buy * 1.005), -int(math.floor(math.log10(quote_increment))))

                        # Ensure the rounded price is at least quote_increment
                        if rounded_sell_estimate < quote_increment:
                            rounded_sell_estimate = quote_increment

                        starting_price_sell = rounded_sell_estimate
                        info_logger.info("Starting price determined for sell order: %s", starting_price_sell)

        elif starting_size_B == 0:
            if current_price > mean24 and starting_size_Q > 0:
                # Market is not favorable for buy order 
                print("Market is not favorable for a buy order now")
                print("Waiting for favorable market conditions for buy order...")
                starting_price_buy = determine_starting_buy_parameters(current_price, lower_bb, starting_size_Q, mean24)

            if current_price < mean24 and starting_size_Q > 0:
                # Market is favorable for buy order
                print("Market is favorable for buy order")
                starting_price_buy = determine_starting_buy_parameters(current_price, lower_bb, starting_size_Q, mean24)

        return starting_price_sell, starting_price_buy

# Indicate that cycle_set_utils.py module loaded successfully
info_logger.info("cycle_set_utils module loaded successfully")
