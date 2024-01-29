# compounding_utils.py
from logging_config import app_logger, info_logger
from config import config_data
from starting_input import user_config
from coinbase_auth import create_signed_request, fetch_historical_data 
from coinbase_utils import fetch_product_stats, get_decimal_places
from order_processing_utils import open_limit_sell_order_processing, open_limit_buy_order_processing, close_limit_buy_order_processing, close_limit_sell_order_processing, open_market_sell_order_processing, open_market_buy_order_processing, close_market_buy_order_processing, close_market_sell_order_processing

# Print a message when the module is loaded
print("Compounding Utils module loading...")

# Define necessary parameters
product_id = user_config["product_id"]
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]
endpoint = endpoint = f'/api/v3/brokerage/products/{product_id}'
method = 'GET'
body = '' # Empty for GET requests
headers = create_signed_request(api_key, api_secret, method, endpoint, body)
product_stats = fetch_product_stats(product_id, api_key, headers)
chart_interval = user_config["chart_interval"]
num_intervals = user_config["num_intervals"]
historical_data = fetch_historical_data(product_id, chart_interval, num_intervals)
closing_prices = []

for entry in historical_data:
    try:
        close_price = float(entry[4])
        closing_prices.append(close_price)
    except ValueError:
        # Handle invalid data (e.g., non-numeric values) here, if needed
        # You can print a message or take other appropriate actions
        pass

current_price = closing_prices[-1]
starting_size_B = user_config["starting_size_B"]
starting_size_Q = user_config["starting_size_Q"]
profit_percent = user_config["profit_percent"]
maker_fee = user_config["maker_fee"]
taker_fee = user_config["taker_fee"]
compound_percent = user_config["compound_percent"]
compounding_option = user_config["compounding_option"]

# Print a message indicating the setup is complete
print("Setup for compounding calculations complete.")

# Function to calculate close limit buy order compounding quote currency amounts
def calculate_close_limit_buy_compounding_amt_Q(total_received_Q, total_spent_B, close_price_buy, maker_fee, quote_increment):
    # Determine number decimal places of quote_increment (an integer)
    decimal_places = get_decimal_places(quote_increment)
    
    # Calculate the amount of quote currency used if no compounding and amount available for compounding for close limit buy order
    no_compounding_Q_limit_clb = round(((total_spent_B * close_price_buy) * (1 - maker_fee)), decimal_places)
    compounding_amt_Q_clb = total_received_Q - no_compounding_Q_limit_clb

    app_logger.info("Amount of quote currency compounded for close cycle limit buy order: %s", compounding_amt_Q_clb)
    app_logger.info("Amount of quote currency to be used if no compounding for close cycle limit buy order: %s", no_compounding_Q_limit_clb)
    
    return compounding_amt_Q_clb, no_compounding_Q_limit_clb

# Function to calculate close market buy order compounding quote currency amounts
def calculate_close_market_buy_compounding_amt_Q(total_received_Q, total_spent_B, close_price_buy, taker_fee, quote_increment):
    # Determine number decimal places of quote_increment (an integer)
    decimal_places = get_decimal_places(quote_increment)
    
    # Calculate the amount of quote currency used if no compounding and amount available for compounding for close market buy order
    no_compounding_Q_market_cmb = round(((total_spent_B * close_price_buy) * (1 - taker_fee)), decimal_places)
    compounding_amt_Q_cmb = total_received_Q - no_compounding_Q_market_cmb

    app_logger.info("Amount of quote currency compounded for close cycle market buy order: %s", compounding_amt_Q_cmb)
    app_logger.info("Amount of quote currency to be used if no compounding for close cycle market buy order: %s", no_compounding_Q_market_cmb)
    
    return compounding_amt_Q_cmb, no_compounding_Q_market_cmb

# Function to calculate close limit sell order compounding base currency amounts
def calculate_close_limit_sell_compounding_amt_B(total_received_B, total_spent_Q, close_price_sell, maker_fee, base_increment):
    # Determine number decimal places of bas_increment (an integer)
    decimal_places = get_decimal_places(base_increment)
    
    # Calculate the amount of base currency used if no compounding and amount available for compounding for close limit sell order
    no_compounding_B_limit_cls = round((total_spent_Q / close_price_sell) * (1 - maker_fee), decimal_places)
    compounding_amt_B_cls = total_received_B - no_compounding_B_limit_cls

    app_logger.info("Amount of base currency compounded for close cycle limit sell order: %s", compounding_amt_B_cls)
    app_logger.info("Amount of base currency to be used if no compounding for close cycle limit sell order: %s", no_compounding_B_limit_cls)

    return compounding_amt_B_cls, no_compounding_B_limit_cls

# Function to calculate close market sell order compounding base currency amounts
def calculate_close_market_sell_compounding_amt_B(total_received_B, total_spent_Q, close_price_sell, taker_fee, base_increment):
    # Determine number decimal places of bas_increment (an integer)
    decimal_places = get_decimal_places(base_increment)
    
    # Calculate the amount of base currency used if no compounding and amount available for compounding for close market sell order
    no_compounding_B_market_cms = round((total_spent_Q / close_price_sell) * (1 - taker_fee), decimal_places)
    compounding_amt_B_cms = total_received_B - no_compounding_B_market_cms

    app_logger.info("Amount of base currency compounded for close cycle market sell order: %s", compounding_amt_B_cms)
    app_logger.info("Amount of base currency to be used if no compounding for close cycle market sell order: %s", no_compounding_B_market_cms)

    return compounding_amt_B_cms, no_compounding_B_market_cms

# Function to determine the next close_size_Q for limit order
def determine_next_close_size_Q_limit(compounding_option, total_received_Q, no_compounding_Q_limit, compounding_amt_Q, compound_percent):
    if compounding_option == "100":
        close_size_Q = total_received_Q
    elif compounding_option == "partial":
        close_size_Q = no_compounding_Q_limit + (compounding_amt_Q * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    
    # Print next close cycle quote currency size
    app_logger.info("Next close cycle limit order quote currency size: %s", close_size_Q)

    return close_size_Q 

# Function to determine the next close_size_B for limit order
def determine_next_close_size_B_limit(compounding_option, total_received_B, no_compounding_B_limit, compounding_amt_B, compound_percent):
    if compounding_option == "100":
        close_size_B = total_received_B
    elif compounding_option == "partial":
        close_size_B = no_compounding_B_limit + (compounding_amt_B * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    
    # Print next close cycle base currency size
    app_logger.info("Next close cycle limit order base currency size: %s", close_size_B)

    return close_size_B 

# Function to determine the next close_size_Q for market order
def determine_next_close_size_Q_market(compounding_option, total_received_Q, no_compounding_Q_market, compounding_amt_Q, compound_percent):
    if compounding_option == "100":
        close_size_Q = total_received_Q
    elif compounding_option == "partial":
        close_size_Q = no_compounding_Q_market + (compounding_amt_Q * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    
    # Print next close cycle quote currency size
    app_logger.info("Next close cycle market order quote currency size: %s", close_size_Q)

    return close_size_Q

# Function to determine the next close_size_B for limit order
def determine_next_close_size_B_market(compounding_option, total_received_B, no_compounding_B_market, compounding_amt_B, compound_percent):
    if compounding_option == "100":
        close_size_B = total_received_B
    elif compounding_option == "partial":
        close_size_B = no_compounding_B_market + (compounding_amt_B * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    
    # Print next close cycle base currency size
    app_logger.info("Next close cycle limit order base currency size: %s", close_size_B)

    return close_size_B 

# Function to calculate open limit sell order compounding base currency amounts
def calculate_open_limit_sell_compounding_amt_B(total_received_B, total_spent_Q, open_price_sell, maker_fee, base_increment):
    # Determine number decimal places of bas_increment (an integer)
    decimal_places = get_decimal_places(base_increment)
    
    # Calculate the amount of base currency used if no compounding and amount available for compounding for open limit sell order
    no_compounding_B_limit_ols = round((total_spent_Q / open_price_sell) * (1 - maker_fee), decimal_places)
    compounding_amt_B_ols = total_received_B - no_compounding_B_limit_ols

    app_logger.info("Amount of base currency compounded for open cycle limit sell order: %s", compounding_amt_B_ols)
    app_logger.info("Amount of base currency to be used if no compounding for open cycle limit sell order: %s", no_compounding_B_limit_ols)

    return compounding_amt_B_ols, no_compounding_B_limit_ols

# Function to calculate open market sell order compounding base currency amounts
def calculate_open_market_sell_compounding_amt_B(total_received_B, total_spent_Q, open_price_sell, taker_fee, base_increment):
    # Determine number decimal places of bas_increment (an integer)
    decimal_places = get_decimal_places(base_increment)
    
    # Calculate the amount of base currency used if no compounding and amount available for compounding for open market sell order
    no_compounding_B_market_oms = round((total_spent_Q / open_price_sell) * (1 - taker_fee), decimal_places)
    compounding_amt_B_oms = total_received_B - no_compounding_B_market_oms

    app_logger.info("Amount of base currency compounded for open cycle market sell order: %s", compounding_amt_B_oms)
    app_logger.info("Amount of base currency to be used if no compounding for open cycle market sell order: %s", no_compounding_B_market_oms)

    return compounding_amt_B_oms, no_compounding_B_market_oms

# Function to calculate open limit buy order compounding quote currency amounts
def calculate_open_limit_buy_compounding_amt_Q(total_received_Q, total_spent_B, open_price_buy, maker_fee, quote_increment):
    # Determine number decimal places of quote_increment (an integer)
    decimal_places = get_decimal_places(quote_increment)
    
    # Calculate the amount of quote currency used if no compounding and amount available for compounding for open limit buy order
    no_compounding_Q_limit_olb = round(((total_spent_B * open_price_buy) * (1 - maker_fee)), decimal_places)
    compounding_amt_Q_olb = total_received_Q - no_compounding_Q_limit_olb

    app_logger.info("Amount of quote currency compounded for open cycle limit buy order: %s", compounding_amt_Q_olb)
    app_logger.info("Amount of quote currency to be used if no compounding for open cycle limit buy order: %s", no_compounding_Q_limit_olb)
    
    return compounding_amt_Q_olb, no_compounding_Q_limit_olb

# Function to calculate open market buy order compounding quote currency amounts
def calculate_open_market_buy_compounding_amt_Q(total_received_Q, total_spent_B, open_price_buy, taker_fee, quote_increment):
    # Determine number decimal places of quote_increment (an integer)
    decimal_places = get_decimal_places(quote_increment)
    
    # Calculate the amount of quote currency used if no compounding and amount available for compounding for open market buy order
    no_compounding_Q_market_omb = round(((total_spent_B * open_price_buy) * (1 - taker_fee)), decimal_places)
    compounding_amt_Q_omb = total_received_Q - no_compounding_Q_market_omb

    app_logger.info("Amount of quote currency compounded for open cycle market buy order: %s", compounding_amt_Q_omb)
    app_logger.info("Amount of quote currency to be used if no compounding for open cycle market buy order: %s", no_compounding_Q_market_omb)
    
    return compounding_amt_Q_omb, no_compounding_Q_market_omb

# Function to determine the next open_size_B
def determine_next_open_size_B_limit(compounding_option, total_received_B, no_compounding_B_limit, compounding_amt_B, compound_percent):
    if compounding_option == "100":
        open_size_B = total_received_B
    elif compounding_option == "partial":
        open_size_B = no_compounding_B_limit + (compounding_amt_B * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    return open_size_B

# Function to determine the next open_size_Q
def determine_next_open_size_Q_limit(compounding_option, total_received_Q, no_compounding_Q_limit, compounding_amt_Q, compound_percent):
    if compounding_option == "100":
        open_size_Q = total_received_Q
    elif compounding_option == "partial":
        open_size_Q = no_compounding_Q_limit + (compounding_amt_Q * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    return open_size_Q

# Function to determine the next open_size_B
def determine_next_open_size_B_market(compounding_option, total_received_B, no_compounding_B_market, compounding_amt_B, compound_percent):
    if compounding_option == "100":
        open_size_B = total_received_B
    elif compounding_option == "partial":
        open_size_B = no_compounding_B_market + (compounding_amt_B * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    return open_size_B

# Function to determine the next open_size_Q
def determine_next_open_size_Q_market(compounding_option, total_received_Q, no_compounding_Q_market, compounding_amt_Q, compound_percent):
    if compounding_option == "100":
        open_size_Q = total_received_Q
    elif compounding_option == "partial":
        open_size_Q = no_compounding_Q_market + (compounding_amt_Q * (compound_percent / 100))
    else:
        raise ValueError("Invalid compounding option")
    return open_size_Q

# Print a message indicating that functions are defined
info_logger.info("Compounding functions defined.")

# Indicate that compounding_utils.py module loaded successfully
info_logger.info("compounding_utils module loaded successfully")
