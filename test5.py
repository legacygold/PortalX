import requests
from coinbase_auth import config_data, create_signed_request
from user_input2 import user_config
from logging_config import app_logger, info_logger, error_logger
from repeating_cycle_utils import determine_next_open_sell_order_price_with_retry, current_rsi
from coinbase_utils import fetch_product_stats

# Define your Coinbase API key
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]

product_id = user_config["product_id"]

# Define the api endpoint and payload (if applicable)
endpoint = f'/api/v3/brokerage/products/{product_id}' # Replace with the actual endpoint
method = 'GET'
body = '' # Empty for GET requests

# Create a signed request using your API credentials
headers = create_signed_request(api_key, api_secret, method, endpoint, body)

def fetch_product_stats(product_id, api_key, headers):

    url = f"https://api.coinbase.com/api/v3/brokerage/products/{product_id}"
    
    try:
        # Create headers with the API key
        headers = {
            'CB-ACCESS-KEY': api_key,
            'Content-Type': 'application/json',
            **headers  # Include other headers passed to the function
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception if the request was not successful
        data = response.json()
        
        # Extract the relevant information from the response
        product_info = {
            "product_id": data["product_id"],
            "price": data["price"],
            "price_percentage_change_24h": data["price_percentage_change_24h"],
            "volume_24h": data["volume_24h"],
            "volume_percentage_change_24h": data["volume_percentage_change_24h"],
            "base_increment": data["base_increment"],
            "quote_increment": data["quote_increment"],
            "quote_min_size": data["quote_min_size"],
            "quote_max_size": data["quote_max_size"],
            "base_min_size": data["base_min_size"],
            "base_max_size": data["base_max_size"],
            "base_name": data["base_name"],
            "quote_name": data["quote_name"],
            "watched": data["watched"],
            "is_disabled": data["is_disabled"],
            "new": data["new"],
            "status": data["status"],
            "cancel_only": data["cancel_only"],
            "limit_only": data["limit_only"],
            "post_only": data["post_only"],
            "trading_disabled": data["trading_disabled"],
            "auction_mode": data["auction_mode"],
            "product_type": data["product_type"],
            "quote_currency_id": data["quote_currency_id"],
            "base_currency_id": data["base_currency_id"],
            "base_display_symbol": data["base_display_symbol"],
            "quote_display_symbol": data["quote_display_symbol"],
            "view_only": data["view_only"],
            "price_increment": data["price_increment"],
        }
        print("Product stats fetched successfully")
        info_logger.info(product_info)
        return product_info
    except requests.exceptions.RequestException as e:
        error_logger.error(f"Error fetching product stats: {e}")
        return None
    
product_stats = fetch_product_stats(user_config["product_id"], api_key, headers)

profit_percent = user_config["profit_percent"]

open_price_sell = determine_next_open_sell_order_price_with_retry(profit_percent, current_rsi, product_stats["quote_increment"], max_iterations=10)

app_logger.info("Open sell order price: %s", open_price_sell)
