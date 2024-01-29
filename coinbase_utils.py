# coinbase_utils.py
import requests
import hmac
import hashlib  # Import hashlib
from config import config_data
from logging_config import app_logger, info_logger, error_logger

# Define your Coinbase API key
api_key = config_data["api_key"]

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
    
def fetch_asset_stats(asset, api_key, headers):

    url = f"https://api.coinbase.com/api/v3/brokerage/products/{asset}-USD"
    
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
        print("Asset stats fetched successfully")
        app_logger.info(f"Current {asset} price: {data['price']}")
        info_logger.info(product_info)
        return product_info
    except requests.exceptions.RequestException as e:
        error_logger.error(f"Error fetching asset stats: {e}")
        return None
    
def get_current_price(product_id, api_key, headers):
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

        # Extract the current price
        current_price = data["price"]
        app_logger.info(f"Current {product_id} price: {current_price}")
        return float(current_price)
    
    except requests.exceptions.RequestException as e:
        error_logger.error(f"Error fetching product stats: {e}")
        return None
def get_current_asset_price(asset, api_key, headers):
    url = f"https://api.coinbase.com/api/v3/brokerage/products/{asset}-USD"
    
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

        # Extract the current price
        current_price = data["price"]
        app_logger.info(f"Current {asset} price: {current_price}")
        return float(current_price)
    
    except requests.exceptions.RequestException as e:
        error_logger.error(f"Error fetching asset stats: {e}")
        return None

def get_order_status(order_id):
    url = f"https://api.coinbase.com/api/v3/brokerage/orders/historical/{order_id}"
    response = requests.get(url)

    if response.status_code == 200:
        order_data = response.json()
        return order_data.get("order", {})
    else:
        # Handle API request failure
        return None
    
def cancel_orders(order_ids):
    url = "https://api.coinbase.com/api/v3/brokerage/orders/batch_cancel"
    payload = {
        "order_ids": order_ids
    }
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        cancel_results = response.json().get("results", [])
        return cancel_results
    else:
        # Handle API request failure
        return None
    
def generate_signature(secret, headers, product_id):
    timestamp = headers['CB-ACCESS-TIMESTAMP']
    method = "GET"  # Adjust if using other HTTP methods
    request_path = f"/products/{product_id}/stats"  # Use headers['product_id']
    body = ""
    message = f"{timestamp}{method}{request_path}{body}"
    signature = hmac.new(secret.encode('utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256).digest()
    
    return signature.hex()

def get_decimal_places(number):
    # Convert the number to a string
    num_str = str(number)

    # Check if there is a decimal point in the string
    if '.' in num_str:
        # Split the string at the decimal point
        decimal_part = num_str.split('.')[1]

        # Return the number of digits in the decimal part
        return len(decimal_part)
    else:
        # If there is no decimal point, return 0
        return 0

# Indicate that coinbase_utils.py module loaded successfully
info_logger.info("coinbase_utils module loaded successfully")
