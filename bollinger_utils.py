# bollinger_utils.py
import json
import http.client
import time
import math
from requests.exceptions import Timeout
from logging_config import app_logger, info_logger, error_logger
from config import config_data
from starting_input import user_config
from coinbase_auth import create_signed_request, fetch_historical_data
from coinbase_utils import fetch_product_stats, get_current_price
from statistics import mean, stdev

# Define your API credentials
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]

# Define config data parameters
product_id = user_config["product_id"]
chart_interval = user_config["chart_interval"]
num_intervals = user_config["num_intervals"]
window_size = user_config["window_size"]

# Define the api endpoint and payload (if applicable)
endpoint = f'/api/v3/brokerage/products/{product_id}'  # Replace with the actual endpoint
method = 'GET'
body = ''  # Empty for GET requests

# Create a signed request using your API credentials
headers = create_signed_request(api_key, api_secret, method, endpoint, body)

# Fetch historical data for the specified chart interval
historical_data = fetch_historical_data(product_id, chart_interval, num_intervals)
product_stats = fetch_product_stats(product_id, api_key, headers)

# Extract the close prices from the historical data
closing_prices = []

for entry in historical_data:
    try:
        close_price = float(entry[4])
        closing_prices.append(close_price)
    except ValueError:
        # Handle invalid data (e.g., non-numeric values) here, if needed
        # You can print a message or take other appropriate actions
        error_logger.error("Error extracting closing prices from historical data")
        pass

# Now you have a list of floats in closing_prices

def calculate_bollinger_bands(closing_prices, window_size, num_std_dev=2):
    # Calculate moving average for the last 'window_size' closing prices
    moving_average = mean(closing_prices[-window_size:])
    info_logger.info("Moving Average: %s", moving_average)

    # Calculate standard deviation for the last 'window_size' closing prices
    std_dev = stdev(closing_prices[-window_size:])
    info_logger.info("Standard Deviation: %s", std_dev)

    upper_bb = moving_average + (num_std_dev * std_dev)
    lower_bb = moving_average - (num_std_dev * std_dev)
    
    info_logger.info("Upper Bollinger Band: %s", upper_bb)
    info_logger.info("Lower Bollinger Band: %s", lower_bb)
    
    return upper_bb, lower_bb

# Function to determine 24 hour mean
def determine_mean24():
    current_time = int(time.time())
    twenty_four_hours_ago = current_time - (24 * 60 * 60)
    high_24hr = float('-inf')
    low_24hr = float('inf')

    historical_data24 = fetch_historical_data(product_id, 86400, 1)

    for entry in historical_data24:
        entry_time = entry[0]
        if twenty_four_hours_ago <= entry_time <= current_time:
            try:
                high = float(entry[2])
                low = float(entry[1])

                if high > high_24hr:
                    high_24hr = high
                if low < low_24hr:
                    low_24hr = low
            except ValueError:
                error_logger.error("Error: unable to determine 24 hr high and low")
                pass

    mean24 = (high_24hr + low_24hr) / 2

    info_logger.info("24 hr High: %s, 24 hr Low: %s", high_24hr, low_24hr)
    info_logger.info("24 hr mean: %s", mean24)

    return mean24

def get_best_bid_ask_prices(api_key, api_secret, product_id, max_retries=3):
    conn = http.client.HTTPSConnection("api.coinbase.com")
    endpoint = f"/api/v3/brokerage/best_bid_ask"
    params = f"?product_ids={product_id}"  # Use product_ids instead of product_id
    headers = create_signed_request(api_key, api_secret, "GET", endpoint, body='')

    retries = 0

    while retries < max_retries:
        try:
            conn.request("GET", endpoint + params, headers=headers)
            res = conn.getresponse()
            data = res.read()

            info_logger.info("get_best_bid_ask_prices raw response data: %s", data.decode("utf-8"))

            if not data:
                error_logger.error("Empty response in get_best_bid_ask_prices.")
                retries += 1
                continue  # Retry if empty response is encountered

            response_json = json.loads(data.decode("utf-8"))
            pricebooks = response_json.get("pricebooks", [])

            if not pricebooks:
                error_logger.error("No 'pricebooks' found in the response.")
                retries += 1
                continue  # Retry if 'pricebooks' is empty

            product_book = pricebooks[0]  # Assuming you want the first entry in the list
            product_id = product_book.get('product_id')
            bids = product_book.get('bids', [])
            asks = product_book.get('asks', [])

            if product_id and bids and asks:
                best_bid = float(bids[0]['price'])
                best_ask = float(asks[0]['price'])
                info_logger.info(f"For {product_id}: Best bid: {best_bid}, Best ask: {best_ask}")
                return best_bid, best_ask
            else:
                error_logger.error("No product_id, bids, or asks found in the response.")

        except Exception as e:
            error_logger.error(f"An error occurred in get_best_bid_ask_prices: {e}")
            retries += 1
            continue  # Retry in case of an exception

    return None  # Return None if max retries are reached without success

def get_best_bid_ask_prices_with_retry(api_key, api_secret, product_id, max_retries=3):
    retries = 0

    while retries < max_retries:
        try:
            # Your existing code to fetch best bid and ask prices
            best_bid, best_ask = get_best_bid_ask_prices(api_key, api_secret, product_id)

            if best_bid and best_ask:
                return best_bid, best_ask
            else:
                print("No bids or asks found in the response. Retrying...")
        except Timeout:
            retries += 1
            print("Timeout occurred. Retrying...")

    error_logger.error("Maximum retries reached. Unable to fetch best bid and ask prices.")
    return None
    
def determine_starting_sell_parameters(current_price, upper_bb, starting_size_B, mean24):
    while True:
        starting_price_sell = calculate_starting_sell_price_with_retry(current_price, upper_bb, starting_size_B, mean24, max_iterations=10)
        
        if starting_price_sell is not None:
            return starting_price_sell
        
        # Wait for a short duration before checking again
        time.sleep(5)  # Adjust the duration as needed

def determine_starting_buy_parameters(current_price, lower_bb, starting_size_Q, mean24):
    while True:
        starting_price_buy = calculate_starting_buy_price_with_retry(current_price, lower_bb, starting_size_Q, mean24, max_iterations=10)
        if starting_price_buy is not None:
            return starting_price_buy
        
        # Wait for a short duration before checking again
        time.sleep(5)  # Adjust the duration as needed

def calculate_starting_sell_price(current_price, upper_bb, starting_size_B, mean24, product_stats, max_iterations=10, timeout=600):
    quote_increment = float(product_stats["quote_increment"])
    start_time = time.time()

    # Initialize the starting sell price
    starting_price_sell = None

    iterations = 0
    while iterations < max_iterations:
        # Check if the timeout has been exceeded
        if time.time() - start_time > timeout:
            raise Timeout("Timeout occurred while waiting for market conditions to be met")

        headers = create_signed_request(api_key, api_secret, method, endpoint, body= '')
        # Recalculate current_price and mean24 inside the loop
        current_price = get_current_price(product_id, api_key, headers)  # Replace with your function to get the current price
        mean24 = determine_mean24()  # Replace with your function to calculate mean24
        upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, window_size, num_std_dev=2)
        
        # Check if criteria is met for determining starting sell price
        if current_price > mean24 and starting_size_B > 0:
            # Calculate the rounded price based on quote_increment
            rounded_price = round((upper_bb * 0.9995), -int(math.floor(math.log10(quote_increment))))

            # Ensure the rounded price is at least quote_increment
            if rounded_price < quote_increment:
                rounded_price = quote_increment

            # Retrieve best bid and ask prices
            best_bid, best_ask = get_best_bid_ask_prices_with_retry(api_key, api_secret, product_id, max_retries=3)

            # Compare with the calculated starting sell price
            if best_bid and rounded_price > best_bid:
                starting_price_sell = rounded_price  # Place a sell order slightly below upper_bb
                info_logger.info("Current price: %s", current_price)
                app_logger.info("Starting price calculated for sell order: %s", starting_price_sell)
                return starting_price_sell  # Exit the loop if conditions are met

            print("Starting sell order price not favorable based on best bid. Continuing to wait...")
        else:    
            print("Criteria for market conditions not met for placing sell order. Continuing to wait...")

        iterations += 1
        time.sleep(90)  # Adjust the sleep time as needed

    print("Maximum iterations reached. Conditions for determining starting sell price not met. Resetting retries.")
    starting_size_Q = user_config["starting_size_Q"]
    from cycle_set_utils import determine_starting_prices
    return determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, quote_increment)

def calculate_starting_sell_price_with_retry(current_price, upper_bb, starting_size_B, mean24, max_iterations=10):
    quote_increment = float(product_stats["quote_increment"])
    iterations = 0

    while iterations < max_iterations:
        try:
            return calculate_starting_sell_price(current_price, upper_bb, starting_size_B, mean24, product_stats, max_iterations=10, timeout=600)
        except Timeout:
            print("Timeout occurred. Retrying...")

        iterations += 1
        time.sleep(90)  # Adjust the sleep time as needed

    print("Maximum iterations reached. Conditions for determining starting sell price not met. Resetting retries.")
    starting_size_Q = user_config["starting_size_Q"]
    upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, window_size, num_std_dev=2)
    from cycle_set_utils import determine_starting_prices
    return determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, quote_increment)

def calculate_starting_buy_price(current_price, lower_bb, starting_size_Q, mean24, product_stats, max_iterations=10, timeout=600):
    quote_increment = float(product_stats["quote_increment"])
    start_time = time.time()
    
    # Initialize the starting buy price
    starting_price_buy = None

    iterations = 0
    while iterations < max_iterations:
        # Check if the timeout has been exceeded
        if time.time() - start_time > timeout:
            raise Timeout("Timeout occurred while waiting for market conditions to be met")

        headers = create_signed_request(api_key, api_secret, method, endpoint, body= '')
        # Recalculate current_price and mean24 inside the loop
        current_price = get_current_price(product_id, api_key, headers)  # Replace with your function to get the current price
        mean24 = determine_mean24()  # Replace with your function to calculate mean24
        upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, window_size, num_std_dev=2)

        # Check if criteria is met for determining starting buy price
        if current_price < mean24 and starting_size_Q > 0:
            # Calculate the rounded price based on quote_increment
            rounded_price = round((lower_bb * 1.0005), -int(math.floor(math.log10(quote_increment))))

            # Ensure the rounded price is at least quote_increment
            if rounded_price < quote_increment:
                rounded_price = quote_increment

            # Retrieve best bid and ask prices
            best_bid, best_ask = get_best_bid_ask_prices_with_retry(api_key, api_secret, product_id, max_retries=3)

            # Compare with the calculated starting sell price
            if best_ask and rounded_price < best_ask:
                starting_price_buy = rounded_price  # Place a buy order slightly above lower_bb
                info_logger.info("Current price: %s", current_price)
                app_logger.info("Starting price calculated for buy order: %s", starting_price_buy)
                return starting_price_buy  # Exit the loop if conditions are met

            print("Starting buy order price not favorable based on best ask. Continuing to wait...")
        else:    
            print("Criteria for market conditions not met for placing buy order. Continuing to wait...")

        iterations += 1
        time.sleep(90)  # Adjust the sleep time as needed

    print("Maximum iterations reached. Conditions for determining starting buy price not met. Resetting retries.")
    starting_size_B = user_config["starting_size_B"]
    from cycle_set_utils import determine_starting_prices
    return determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, quote_increment)

def calculate_starting_buy_price_with_retry(current_price, lower_bb, starting_size_Q, mean24, max_iterations=10):
    quote_increment = float(product_stats["quote_increment"])
    iterations = 0

    while iterations < max_iterations:
        try:
            return calculate_starting_buy_price(current_price, lower_bb, starting_size_Q, mean24, product_stats, max_iterations=10, timeout=600)
        except Timeout:
            print("Timeout occurred. Retrying...")

        iterations += 1
        time.sleep(5)  # Adjust the sleep time as needed

    print("Maximum iterations reached. Conditions for determining starting buy price not met. Resetting retries.")
    starting_size_B = user_config["starting_size_B"]
    upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, window_size, num_std_dev=2)
    from cycle_set_utils import determine_starting_prices
    return determine_starting_prices(current_price, upper_bb, lower_bb, starting_size_B, starting_size_Q, mean24, quote_increment)


# Indicate that bollinger_utils.py module loaded successfully
info_logger.info("bollinger_utils module loaded successfully")
