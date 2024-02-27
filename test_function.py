# test_function.py

import time
import pandas as pd
from requests.exceptions import Timeout
from logging_config import app_logger
from config import config_data
from starting_input import user_config
from coinbase_auth import create_signed_request, fetch_historical_data
from coinbase_utils import fetch_product_stats
from tradingview_ta_utils import create_ta_handler_instance, get_ta_handler_analysis

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
        time.sleep(300)

    # Calculate price changes
    delta = pd.Series(closing_prices).diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Calculate the Exponential Moving Average (EMA) for gains and losses
    avg_gain = gain.ewm(span=period, adjust=False).mean() # Using EMA
    avg_loss = loss.ewm(span=period, adjust=False).mean() # Using EMA

    # Compute the Relative Strength (RS)
    rs = avg_gain / avg_loss

    # Calculate the RSI
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]  # Return the last RSI value

def calculate_rsi(product_id, chart_interval, length):
    while True:
        # Print statement to indicate RSI calculation
        print("Fetching RSI data...")

        # Define your desired time frame
        total_data_points = 400 * chart_interval  # Slightly increased to ensure enough data
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

# Example usage:
handler = create_ta_handler_instance()
analysis = get_ta_handler_analysis(handler)
print("RSI: ", analysis.indicators["RSI"])

rsi_value = new_calculate_rsi(closing_prices)
print("Current RSI Value:", rsi_value)

length = 360 * chart_interval
rsi = calculate_rsi(product_id, chart_interval, length)
print("Current RSI: ", rsi)



