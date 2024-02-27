# repeating_cycle_utils.py
import uuid
import requests
import math
from requests.auth import AuthBase
import hmac
import hashlib
import json
import time
import pandas as pd
from requests.exceptions import Timeout
from logging_config import app_logger, info_logger, error_logger
from config import config_data
from starting_input import user_config
from coinbase_auth import create_signed_request, fetch_historical_data
from coinbase_utils import fetch_product_stats, get_current_price
from bollinger_utils import calculate_bollinger_bands, get_best_bid_ask_prices_with_retry

# Print statement to indicate module loading
print("Loading repeating_cycle_utils module")

# Define API credentials
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]
api_url = 'https://api.coinbase.com'
orderep = '/api/v3/brokerage/orders'

# Define config data parameters
product_id = user_config["product_id"]
starting_size_B = user_config["starting_size_B"]
starting_size_Q = user_config["starting_size_Q"]
profit_percent = user_config["profit_percent"]
maker_fee = user_config["maker_fee"]
taker_fee = user_config["taker_fee"]
chart_interval = user_config["chart_interval"]
num_intervals = user_config["num_intervals"]
window_size = user_config["window_size"]

# Print statement to indicate fetching historical data
app_logger.info("Fetching historical data for %s", product_id)

# Fetch historical data for the specified chart interval
historical_data = fetch_historical_data(product_id, chart_interval, num_intervals)

# Define the api endpoint and payload (if applicable)
endpoint = f'/api/v3/brokerage/products/{product_id}' # Replace with the actual endpoint
method = 'GET'
body = '' # Empty for GET requests

# Create a signed request using your API credentials
headers = create_signed_request(api_key, api_secret, method, endpoint, body)

# Fetch the latest product stats from Coinbase API with error handling
app_logger.info("Fetching product stats for %s", product_id)
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
        pass

# Get current price, Bollinger bands, 24 hr mean, and starting prices
bollinger_data = closing_prices
current_price = closing_prices[0]
upper_bb, lower_bb = calculate_bollinger_bands(bollinger_data, user_config["window_size"], num_std_dev=2)

def calculate_long_term_ma24(product_id):
    # Fetch historical data for the specified product with a 24-hour interval
    historical_data24 = fetch_historical_data(product_id, 3600, 24)

    # Extract the close prices from the 24-hour historical data
    closing_prices24 = []
    
    for entry in historical_data24:
        try:
            close_price = float(entry[4])
            closing_prices24.append(close_price)
        except ValueError:
            # Handle invalid data (e.g., non-numeric values) here, if needed
            pass

    if len(closing_prices24) < 24:
        error_logger.error("Not enough data to return 24 hour closing prices")
        time.sleep(300)  # Wait for 5 minutes before retrying

    # Calculate the 24-hour moving average
    long_term_ma24 = sum(closing_prices24) / 24

    return long_term_ma24

# Print statement to indicate 24-hour MA calculation
print("Calculating 24-hour moving average...")

# Define long term 24 hour moving average to determine trend
long_term_ma24 = calculate_long_term_ma24(product_id)
app_logger.info("Long term 24 hour moving average: %s", long_term_ma24)

def calculate_rsi(product_id, chart_interval, length):
    while True:
        # Print statement to indicate RSI calculation
        print("Fetching RSI data...")

        # Define your desired time frame
        total_data_points = 24000  # Slightly increased to ensure enough data
        candles_per_request = 300  # Maximum candles per request

        # Calculate how many requests are needed
        num_requests = total_data_points // candles_per_request

        # Initialize an empty list to collect closing prices
        closing_prices = []

        # Initialize the end_time to the current time
        end_time = int(time.time())

        # Make API requests and collect closing prices
        for _ in range(num_requests):
            # Calculate start_time based on end_time and the desired time frame
            start_time = end_time - (chart_interval * candles_per_request)

            # Make an API request and get historical data
            data = fetch_historical_data(product_id, chart_interval, candles_per_request)

            # Extract closing prices and append to the list
            closing_prices.extend([entry[4] for entry in data])

            # Update end_time for the next request
            end_time = start_time

        # Ensure we have enough data points for the calculation
        if len(closing_prices) >= length:
            break  # Exit the loop if we have enough data

        # If we don't have enough data, wait for some time before retrying
        print("Insufficient data points for RSI calculation. Retrying in 5 minutes...")
        time.sleep(300)  # Wait for 5 minutes before retrying

    # Fill missing or zero values in closing prices with a default value (e.g., 0.0)
    closing_prices = pd.Series(closing_prices).fillna(0.0).tolist()

    # Calculate price changes
    delta = pd.Series(closing_prices).diff(1)
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Filter out zero values from gains and losses
    gains = gains[gains != 0]
    losses = losses[losses != 0]

    # Calculate average gains and losses
    avg_gain = gains.sum() / len(gains)
    avg_loss = losses.sum() / len(losses)

    # Calculate relative strength (RS)
    rs = avg_gain / avg_loss

    # Calculate RSI
    rsi = 100 - (100 / (1 + rs))

    app_logger.info(f"Calculated RSI for {product_id}, interval {chart_interval}, length {length}: {rsi}")

    return rsi

def new_calculate_rsi(closing_prices, period=14):
    """
    Calculate the Relative Strength Index (RSI) for a given list of closing prices.
    
    Parameters:
    - closing_prices: List of closing prices for a given product.
    - period: Number of periods to use for RSI calculation, default is 14.
    
    Returns:
    - RSI value.
    """
    if len(closing_prices) < period:
        print("Insufficient data points for RSI calculation.")
        return None

    # Convert the closing prices to a Pandas Series
    prices = pd.Series(closing_prices)

    # Calculate price changes
    delta = prices.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate the average gain and average loss
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    # Calculate the Relative Strength (RS)
    rs = avg_gain / avg_loss

    # Calculate the Relative Strength Index (RSI)
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]  # Return the last RSI value

# Example usage:
rsi_value = new_calculate_rsi(closing_prices)
print("Current RSI Value:", rsi_value)

# Define current RSI
rsi = calculate_rsi(product_id, chart_interval, length=21600)  # 15 days worth of 1-minute data
current_rsi = rsi

def determine_next_open_sell_order_price(profit_percent, current_rsi, quote_increment, max_iterations=10, timeout=600):
    quote_increment = float(product_stats["quote_increment"])
    start_time = time.time()

    # Print statement to indicate opening price determination
    print("Determining next opening cycle sell order price...")

    # Initialize next opening cycle sell order prices
    open_price_sell = None

    iterations = 0
    while iterations < max_iterations:
        # Check if the timeout has been exceeded
        if time.time() - start_time > timeout:
            raise Timeout("Timeout occurred while waiting for market conditions to be met")
        
        headers = create_signed_request(api_key, api_secret, method, endpoint, body= '')
        # Recalculate current_price and mean24 inside the loop
        current_price = get_current_price(product_id, api_key, headers)  # Replace with your function to get the current price
        long_term_ma24 = calculate_long_term_ma24(product_id)  # Replace with your function to calculate mean24

        # Determine trend direction
        upward_trend = current_price > long_term_ma24

        # Check scenarios based on trend and RSI
        if upward_trend:
            while current_rsi <= 50:
                # Keep checking RSI until it's greater than 50
                current_rsi = calculate_rsi(product_id, chart_interval, length=21600)  # Update RSI value
                time.sleep(90)  # Wait for a while before checking again

            # Trend is upward, RSI > 50
            upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, user_config["window_size"], num_std_dev=2)
            open_price_sell = float(round(max(current_price * (1 + profit_percent), 1.001 * upper_bb), -int(math.floor(math.log10(float(quote_increment))))))
        else:
            while current_rsi <= 50:
                # Keep checking RSI until it's greater than or equal to 50
                current_rsi = calculate_rsi(product_id, chart_interval, length=21600)  # Update RSI value
                time.sleep(90)  # Wait for a while before checking again

            # Trend is downward, RSI > 50
            upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, user_config["window_size"], num_std_dev=2)
            open_price_sell = float(round(min(current_price * (1 + profit_percent), 0.999 * upper_bb), -int(math.floor(math.log10(float(quote_increment))))))

        if open_price_sell is not None:
            # Retrieve best bid and ask prices
            best_bid, best_ask = get_best_bid_ask_prices_with_retry(api_key, api_secret, product_id, max_retries=3)

            # Compare with the calculated starting sell price
            if best_bid and open_price_sell > best_bid:
                app_logger.info("Next opening cycle sell price: %s", open_price_sell)
                return open_price_sell
            else:
                print("Opening cycle price not favorable based on best bid. Continuing to wait...")

        time.sleep(90)  # Adjust the sleep time as needed

def determine_next_open_sell_order_price_with_retry(profit_percent, current_rsi, quote_increment, iterations=0, depth=0, max_iterations=10, max_depth=1000000):

    while iterations < max_iterations:
        try:
            return determine_next_open_sell_order_price(profit_percent, current_rsi, quote_increment, max_iterations=10, timeout=600)
        except Timeout:
            print("Timeout occurred. Retrying...")

        iterations += 1
        time.sleep(90)  # Adjust the sleep time as needed

    print("Maximum iterations reached. Conditions for determining opening sell price not met.")
    return determine_next_open_sell_order_price_with_retry(profit_percent, current_rsi, quote_increment, iterations, depth + 1, max_iterations, max_depth)
    
def determine_next_open_buy_order_price(profit_percent, current_rsi, quote_increment, max_iterations=10, timeout=600):
    quote_increment = float(product_stats["quote_increment"])
    start_time = time.time()

    # Print statement to indicate opening price determination
    print("Determining next opening cycle buy order price...")

    # Initialize next opening cycle buy order price
    open_price_buy = None

    iterations = 0
    while iterations < max_iterations:
        # Check if the timeout has been exceeded
        if time.time() - start_time > timeout:
            raise Timeout("Timeout occurred while waiting for market conditions to be met. Resetting retries...")
        
        headers = create_signed_request(api_key, api_secret, method, endpoint, body='')
        # Recalculate current_price and mean24 inside the loop
        current_price = get_current_price(product_id, api_key, headers)  # Replace with your function to get the current price
        long_term_ma24 = calculate_long_term_ma24(product_id)  # Replace with your function to calculate mean24

        # Determine trend direction
        upward_trend = current_price > long_term_ma24

        # Check scenarios based on trend and RSI
        if upward_trend:
            while current_rsi >= 50:
                # Keep checking RSI until it's less than 50
                current_rsi = calculate_rsi(product_id, chart_interval, length=21600)  # Update RSI value
                time.sleep(90)  # Wait for a while before checking again

            # Trend is upward, RSI < 50
            upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, user_config["window_size"], num_std_dev=2)
            open_price_buy = float(round(max(current_price * (1 - profit_percent), 1.001 * lower_bb), -int(math.floor(math.log10(float(quote_increment))))))

        else:
            while current_rsi >= 50:
                # Keep checking RSI until it's less than 50
                current_rsi = calculate_rsi(product_id, chart_interval, length=21600)  # Update RSI value
                time.sleep(90)  # Wait for a while before checking again

            # Trend is downward, RSI < 50
            upper_bb, lower_bb = calculate_bollinger_bands(closing_prices, user_config["window_size"], num_std_dev=2)
            open_price_buy = float(round(min(current_price * (1 - profit_percent), 0.999 * lower_bb), -int(math.floor(math.log10(float(quote_increment))))))

        if open_price_buy is not None:
            # Retrieve best bid and ask prices
            best_bid, best_ask = get_best_bid_ask_prices_with_retry(api_key, api_secret, product_id, max_retries=3)

            # Compare with the calculated starting sell price
            if best_ask and open_price_buy < best_ask:
                app_logger.info("Next opening cycle buy price: %s", open_price_buy)
                return open_price_buy
            else:
                print("Opening cycle price not favorable based on best ask. Continuing to wait...")

        time.sleep(90)  # Adjust the sleep time as needed

def determine_next_open_buy_order_price_with_retry(profit_percent, current_rsi, quote_increment, iterations=0, depth=0, max_iterations=10, max_depth=1000000):

    while iterations < max_iterations:
        try:
            return determine_next_open_buy_order_price(profit_percent, current_rsi, quote_increment, max_iterations=10, timeout=600)
        except Timeout:
            print("Timeout occurred. Retrying...")

        iterations += 1
        time.sleep(90)  # Adjust the sleep time as needed

    print("Maximum iterations reached. Conditions for determining opening buy price not met. Resetting retries...")
    return determine_next_open_buy_order_price_with_retry(profit_percent, current_rsi, quote_increment, iterations, depth + 1, max_iterations, max_depth)

def place_next_opening_cycle_sell_order(api_key, api_secret, product_id, open_size_B, open_price_sell):
    
    # Print statement to indicate opening cycle order placement
    print("Loading place_next_opening_cycle_sell_order...")

    unique_id = str(uuid.uuid4())  # Generate a unique identifier for the order
    info_logger.info("Unique ID created: %s", unique_id)

    payload = {
        "side": "SELL",
        "order_configuration": {
            "limit_limit_gtc": {
                "base_size": str(open_size_B),
                "limit_price": str(open_price_sell),
                "post_only": True
            },
        },
        "product_id": product_id,
        "client_order_id": unique_id
    }
    
    info_logger.info("Payload: %s", payload)

    class CBAuth(AuthBase):

        def __init__(self, api_secret, api_key, orderep):
            # setup any auth-related data here
            self.api_secret = api_secret
            self.api_key = api_key
            self.api_url = orderep

        def __call__(self, request):
            timestamp = str(int(time.time()))
            message = timestamp + request.method + self.api_url + json.dumps(payload)
            signature = hmac.new(self.api_secret.encode(
                'utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()

            request.headers.update({
                'CB-ACCESS-SIGN': signature.hex(),
                'CB-ACCESS-TIMESTAMP': timestamp,
                'CB-ACCESS-KEY': api_key,
                'accept': "application/json"

            })

            return request

    try:
        auth = CBAuth(api_secret, api_key, orderep)
        r = requests.post(api_url + orderep, json=payload, auth=auth)  # .json()
        info_logger.info(r)
        info_logger.info(r.status_code)
        info_logger.info(r.content)

        response_json = r.json()
        print(response_json)  # Print the JSON response

        if r.status_code == 200 and response_json.get("success") == True:
            order_id = response_json.get("order_id")
            app_logger.info("Next opening cycle sell order placed. Order ID: %s", order_id)
            return order_id
        else:
            error_logger.error(f"Error placing next opening cycle sell order - Status Code: {r.status_code}")
            return None
        
    except requests.exceptions.RequestException as e:
        error_logger.error(f"An error occurred in place_next_opening_cycle_sell_order: {e}")
        return None
    except json.JSONDecodeError as e:
        error_logger.error(f"Error decoding JSON response in place_next_opening_cycle_sell_order: {e}")
        return None
    except Exception as e:
        error_logger.error(f"An error occurred in place_next_opening_cycle_sell_order: {e}")
        return None

def place_next_opening_cycle_buy_order(api_key, api_secret, product_id, open_size_Q, maker_fee, open_price_buy, product_stats):
    
    # Print statement to indicate opening cycle order placement
    print("Loading place_next_opening_cycle_buy_order...")

    base_increment = product_stats["base_increment"]
    
    # Calculate base_size_Q
    print("Calculating base_size_Q...")
    info_logger.info("open_size_Q = %s, maker_fee = %s, open_price_buy = %s", open_size_Q, maker_fee, open_price_buy)
    if isinstance(open_size_Q, (int, float)) and isinstance(maker_fee, (int, float)) and isinstance(open_price_buy, (int, float)):
        base_size_Q = int((starting_size_Q * (1 - maker_fee) / open_price_buy)) / float(base_increment) * float(base_increment)
        app_logger.info("Base size calculated successfully: %s", base_size_Q)
    else:
        error_logger.error("Invalid input types in the calculation of base_size_Q.")
        return None  # Return None to indicate failure

    unique_id = str(uuid.uuid4())  # Generate a unique identifier for the order
    info_logger.info("Unique ID created: %s", unique_id)

    payload = {
        "side": "BUY",
        "order_configuration": {
            "limit_limit_gtc": {
                "base_size": str(base_size_Q),
                "limit_price": str(open_price_buy),
                "post_only": True
            },
        },
        "product_id": product_id,
        "client_order_id": unique_id
    }

    info_logger.info("Payload: %s", payload)

    class CBAuth(AuthBase):

        def __init__(self, api_secret, api_key, orderep):
            # setup any auth-related data here
            self.api_secret = api_secret
            self.api_key = api_key
            self.api_url = orderep

        def __call__(self, request):
            timestamp = str(int(time.time()))
            message = timestamp + request.method + self.api_url + json.dumps(payload)
            signature = hmac.new(self.api_secret.encode(
                'utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()

            request.headers.update({
                'CB-ACCESS-SIGN': signature.hex(),
                'CB-ACCESS-TIMESTAMP': timestamp,
                'CB-ACCESS-KEY': api_key,
                'accept': "application/json"

            })

            return request

    try:
        auth = CBAuth(api_secret, api_key, orderep)
        r = requests.post(api_url + orderep, json=payload, auth=auth)  # .json()
        info_logger.info(r)
        info_logger.info(r.status_code)
        info_logger.info(r.content)

        response_json = r.json()
        print(response_json)  # Print the JSON response

        if r.status_code == 200 and response_json.get("success") == True:
            order_id = response_json.get("order_id")
            app_logger.info("Next opening cycle buy order placed. Order ID: %s", order_id)
            return order_id
        else:
            error_logger.error(f"Error placing next opening cycle buy order - Status Code: {r.status_code}")
            return None
        
    except requests.exceptions.RequestException as e:
        error_logger.error(f"An error occurred in place_next_opening_cycle_buy_order: {e}")
        return None
    except json.JSONDecodeError as e:
        error_logger.error(f"Error decoding JSON response in place_next_opening_cycle_buy_order: {e}")
        return None
    except Exception as e:
        error_logger.error(f"An error occurred in place_next_opening_cycle_buy_order: {e}")
        return None

def place_next_closing_cycle_buy_order(api_key, api_secret, product_id, close_size_Q, maker_fee, close_price_buy, product_stats):
    try:
        # Print statement to indicate closing cycle order placement
        print("Loading place_next_closing_cycle_buy_order...")

        base_increment = product_stats["base_increment"]

        # Calculate base_size_Q
        print("Calculating base_size_Q...")
        info_logger.info("close_size_Q = %s, maker_fee = %s, close_price_buy = %s", close_size_Q, maker_fee, close_price_buy)
        if isinstance(close_size_Q, (int, float)) and isinstance(maker_fee, (int, float)) and isinstance(close_price_buy, (int, float)):
            base_size_Q = int((close_size_Q * (1 - maker_fee) / close_price_buy)) / float(base_increment) * float(base_increment)
            app_logger.info("Base size calculated successfully: %s", base_size_Q)
        else:
            error_logger.error("Invalid input types in the calculation of base_size_Q.")
            return None  # Return None to indicate failure

        unique_id = str(uuid.uuid4())  # Generate a unique identifier for the order
        info_logger.info("Unique ID created: %s", unique_id)

        payload = {
            "side": "BUY",
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size": str(base_size_Q),
                    "limit_price": str(close_price_buy),
                    "post_only": True
                },
            },
            "product_id": product_id,
            "client_order_id": unique_id
        }

        info_logger.info("Payload: %s", payload)

        class CBAuth(AuthBase):

            def __init__(self, api_secret, api_key, orderep):
                # setup any auth-related data here
                self.api_secret = api_secret
                self.api_key = api_key
                self.api_url = orderep

            def __call__(self, request):
                timestamp = str(int(time.time()))
                message = timestamp + request.method + self.api_url + json.dumps(payload)
                signature = hmac.new(self.api_secret.encode(
                    'utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()

                request.headers.update({
                    'CB-ACCESS-SIGN': signature.hex(),
                    'CB-ACCESS-TIMESTAMP': timestamp,
                    'CB-ACCESS-KEY': api_key,
                    'accept': "application/json"
                })

                return request

        auth = CBAuth(api_secret, api_key, orderep)
        r = requests.post(api_url + orderep, json=payload, auth=auth)  # .json()
        info_logger.info(r)
        info_logger.info(r.status_code)
        info_logger.info(r.content)

        if r.status_code == 200:
            order_details = r.json()
            order_id = order_details.get("order_id")
            app_logger.info("Next closing cycle buy order placed. Order ID: %s", order_id)

            return order_id
        else:
            error_logger.error(f"Error placing next closing cycle buy order - Status Code: {r.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        error_logger.error(f"An error occurred in place_next_closing_cycle_buy_order: {e}")
        return None
    except json.JSONDecodeError as e:
        error_logger.error(f"Error decoding JSON response in place_next_closing_cycle_buy_order: {e}")
        return None
    except Exception as e:
        error_logger.error(f"An unexpected error occurred in place_next_closing_cycle_buy_order: {e}")
        return None

def place_next_closing_cycle_sell_order(api_key, api_secret, product_id, close_size_B, close_price_sell):
    try:
        # Print statement to indicate opening cycle order placement
        print("Loading place_next_closing_cycle_sell_order...")

        unique_id = str(uuid.uuid4())  # Generate a unique identifier for the order
        info_logger.info("Unique ID created: %s", unique_id)

        payload = {
            "side": "SELL",
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size": str(close_size_B),
                    "limit_price": str(close_price_sell),
                    "post_only": True
                },
            },
            "product_id": product_id,
            "client_order_id": unique_id
        }

        info_logger.info("Payload: %s", payload)

        class CBAuth(AuthBase):

            def __init__(self, api_secret, api_key, orderep):
                # setup any auth-related data here
                self.api_secret = api_secret
                self.api_key = api_key
                self.api_url = orderep

            def __call__(self, request):
                timestamp = str(int(time.time()))
                message = timestamp + request.method + self.api_url + json.dumps(payload)
                signature = hmac.new(self.api_secret.encode(
                    'utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()

                request.headers.update({
                    'CB-ACCESS-SIGN': signature.hex(),
                    'CB-ACCESS-TIMESTAMP': timestamp,
                    'CB-ACCESS-KEY': api_key,
                    'accept': "application/json"

                })

                return request

        auth = CBAuth(api_secret, api_key, orderep)
        r = requests.post(api_url + orderep, json=payload, auth=auth)  # .json()
        info_logger.info(r)
        info_logger.info(r.status_code)
        info_logger.info(r.content)

        if r.status_code == 200:
            order_details = r.json()
            order_id = order_details.get("order_id")
            app_logger.info("Next closing cycle sell order placed. Order ID: %s", order_id)

            return order_id
        else:
            error_logger.info(f"Error placing next closing cycle sell order - Status Code: {r.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        error_logger.error(f"An error occurred in place_next_closing_cycle_sell_order: {e}")
        return None
    except json.JSONDecodeError as e:
        error_logger.error(f"Error decoding JSON response in place_next_closing_cycle_sell_order: {e}")
        return None
    except Exception as e:
        error_logger.error(f"An unexpected error occurred in place_next_closing_cycle_sell_order: {e}")
        return None

# Print statement to indicate module completion
info_logger.info("repeating_cycle_utils module loaded successfully")
