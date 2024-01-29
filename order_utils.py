#order_utils.py
from logging_config import app_logger, info_logger, error_logger
import uuid
import requests
from requests.auth import AuthBase
from requests.exceptions import RequestException
import hmac
import hashlib
import http.client
import json
import time
from config import config_data
from starting_input import user_config
from coinbase_auth import create_signed_request, fetch_historical_data
from error_handling_utils import handle_error_and_return_to_main_loop

# Define API credentials
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]
api_url = 'https://api.coinbase.com'
orderep = '/api/v3/brokerage/orders'

# Define other order parameters
product_id = user_config["product_id"]
maker_fee = user_config["maker_fee"]
taker_fee = user_config["taker_fee"]
chart_interval = user_config["chart_interval"]
num_intervals = user_config["num_intervals"]
window_size = user_config["window_size"]
historical_data = fetch_historical_data(product_id, chart_interval, num_intervals)

# Extract the close prices from the historical data
closing_prices = []

for entry in historical_data:
    try:
        close_price = float(entry[4])
        closing_prices.append(close_price)
    except ValueError:
        # Handle invalid data (e.g., non-numeric values) here, if needed
        # You can print a message or take other appropriate actions
        error_logger.error("Invalid data entry in historical_data: %s", entry)
        pass

# Now you have a list of floats in closing_prices

# Function for placing starting (cycle 1) opening cycle sell order(s)
def place_starting_open_sell_order(product_id, starting_size_B, starting_price_sell):
    print("Loading place_starting_open_sell_order...")

    unique_id = str(uuid.uuid4())  # Generate a unique identifier for the order
    info_logger.info("Unique ID created: %s", unique_id)

    payload = {
        "side": "SELL",
        "order_configuration": {
            "limit_limit_gtc": {
                "base_size": str(starting_size_B),
                "limit_price": str(starting_price_sell),
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

        if r.status_code == 200:
            order_details = r.json()
            order_id = order_details.get("order_id")
            if order_id is not None and order_details.get("success") == True:
                info_logger.info("Starting opening cycle sell order placed. Order ID: %s", order_id)

                return order_id
        
            else:
                error_logger.error(f"Error placing starting opening cycle sell order - Status Code: {r.status_code}")
                return None
                       
        else:
            error_logger.error(f"Error placing starting opening cycle sell order - Status Code: {r.status_code}")
            return None

    except Exception as e:
        error_logger.error(f"An error occurred in place_starting_open_sell_order: {e}")
        return None

# Function for placing starting (cycle 1) opening cycle buy order(s)
def place_starting_open_buy_order(product_id, product_stats, starting_size_Q, starting_price_buy, maker_fee):
    print("Loading place_starting_open_buy_order...")
    base_increment = product_stats["base_increment"]
    
    # Calculate base_size_Q
    print("Calculating base_size_Q...")
    info_logger.info("starting_size_Q = %s, maker_fee = %s, starting_price_buy = %s", starting_size_Q, maker_fee, starting_price_buy)
    if isinstance(starting_size_Q, (int, float)) and isinstance(maker_fee, (int, float)) and isinstance(starting_price_buy, (int, float)):
        base_size_Q = int((starting_size_Q * (1 - maker_fee) / starting_price_buy)) / float(base_increment) * float(base_increment)
        info_logger.info("Base size calculated successfully: %s", base_size_Q)
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
                "limit_price": str(starting_price_buy),
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

        if r.status_code == 200:
            order_details = r.json()
            order_id = order_details.get("order_id")
            if order_id is not None and order_details.get("success") == True:
                info_logger.info("Starting opening cycle buy order placed. Order ID: %s", order_id)

                return order_id

            else:
                error_logger.error(f"Error placing starting opening cycle buy order - Status Code: {r.status_code}")
                return None
       
        else:
            error_logger.error(f"Error placing starting opening cycle buy order - Status Code: {r.status_code}")
            return None

    except Exception as e:
        error_logger.error(f"An error occurred in place_starting_open_buy_order: {e}")
        return None

def waiting_period_conditions(unit, interval):
    print("Loading waiting_period_conditions...")
    if unit == 'minutes':
        waiting_period = interval * 60
    elif unit == 'hours':
        waiting_period = interval * 3600
    elif unit == 'days':
        waiting_period = interval * 86400
    else:
        raise ValueError("Invalid unit. Please use 'minutes', 'hours', or 'days'.")

    start_time = time.time()
    elapsed_time = 0

    while elapsed_time < waiting_period:
        # Check elapsed time
        elapsed_time = time.time() - start_time

        # Add a sleep to avoid constant checking and reduce CPU usage
        time.sleep(1)  # Sleep for 1 second between checks

    return waiting_period, elapsed_time

def retry_request(func, max_retries=3, initial_delay=5):
    attempts = 0

    while attempts < max_retries:
        try:
            return func()
        except RequestException as e:
            print(f"An error occurred: {e}")
            print(f"Retry attempt {attempts + 1}/{max_retries}")
            time.sleep(initial_delay * (2 ** attempts))
            attempts += 1

    print("Maximum retry attempts reached. Exiting.")
    exit(1)

# Now, you can use waiting_period and elapsed_time as needed in your logic.
# Once waiting_period is reached, you can initiate secondary logic.

def get_order_details(conn, api_key, api_secret, order_id, max_retries):
    headers = create_signed_request(str(api_key), api_secret, "GET", f"/api/v3/brokerage/orders/historical/{order_id}", body='')

    # Retry logic with exponential backoff
    retries = 0
    while True:
        try:
            conn.request("GET", f"/api/v3/brokerage/orders/historical/{order_id}", headers=headers)
            res = conn.getresponse()
            data = res.read()

            if not data:
                error_logger.error("Empty response in get_order_details.")
                error_logger.error(f"Status code: {res.status}")
                raise RequestException("Empty response")

            return json.loads(data.decode("utf-8"))

        except RequestException as e:
            error_logger.error(f"An error occurred in get_order_details: {e}")
            error_logger.error(f"Status code: {res.status}")

            if retries >= max_retries:
                error_logger.error("Max retries reached in get_order_details. Automation process disrupted. Orders may need manual handling.")
                print("Max retries reached in get_order_details. Automation process disrupted. Orders may need manual handling.")
                return None

            retries += 1
            wait_time = 5 * (2 ** retries)
            time.sleep(wait_time)

def wait_for_order(api_key, api_secret, order_id, max_retries=3):
    from trading_record_manager import handle_options_menu
    print("Loading wait_for_order...")
    conn = http.client.HTTPSConnection("api.coinbase.com")

    # Initial request to get order details with retry logic
    order_details = retry_request(lambda: get_order_details(conn, api_key, api_secret, order_id, max_retries), max_retries, initial_delay=5)
    
    if order_details is None:
        return None  # Exit the function if the initial order is not found

    # Print the order details
    app_logger.info("Initial order details: %s", order_details["order"])

    if order_details["order"]["status"] == "OPEN":
        print("Waiting for order to fill...")
        try:
            # Call for 'Options menu' while waiting for order(s) to fill
            handle_options_menu()

        except Exception as e:
            handle_error_and_return_to_main_loop()       

    elif order_details["order"]["status"] == "CANCELLED":
        print("Order cancelled. Check exchange and handle orders manually or retry entering trading data.")

    while True:
        try:
            # Resend the request to get the latest order details
            order_details = get_order_details(conn, api_key, api_secret, order_id, max_retries)

            if order_details is None:
                continue  # Retry if empty response is encountered

            # Check if the "order" key exists in the order_details dictionary
            if "order" in order_details and "status" in order_details["order"]:
                # Check if the order status is FILLED and completion percentage is 100
                if (
                    order_details["order"]["status"] == "FILLED"
                    and float(order_details["order"].get("completion_percentage", 0)) == 100
                ):
                    app_logger.info("Current order status: %s", order_details["order"]["status"])
                    app_logger.info("Order filled successfully. Order details: %s", order_details)
                    return order_details
                else:
                    # If the order is not filled yet or completion percentage is not 100, wait and check again
                    time.sleep(10)
            else:
                # If the "order" or "status" key is not found, log the error and retry
                error_logger.error("Order status not found.")
                time.sleep(10)  # Add a delay before retrying

        except Exception as e:
            error_logger.error(f"An error occurred in wait_for_order: {e}")
            time.sleep(10)  # Add a delay before retrying
    
# Indicate that order_utils.py module loaded successfully
info_logger.info("order_utils module loaded successfully")
