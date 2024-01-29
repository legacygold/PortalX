# test.py
import time
import json
import http.client
from logging_config import app_logger, error_logger
from config import config_data
from coinbase_auth import create_signed_request

# Define your API credentials and other settings here
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]
order_id = "54d9b8e0-41d2-4e12-9b4f-86bb28eb2442"

# Function to wait for order(s) to fill
def wait_for_order(api_key, api_secret, order_id):
    print("Loading wait_for_order...")
    conn = http.client.HTTPSConnection("api.coinbase.com")
    url = f"/api/v3/brokerage/orders/historical/{order_id}"  # Updated URL
    headers = create_signed_request(str(api_key), api_secret, "GET", url, body='')

    try:
        retries = 3  # Number of times to retry fetching order status
        while retries > 0:
            conn.request("GET", url, headers=headers)
            res = conn.getresponse()
            data = res.read()
            order_details = json.loads(data.decode("utf-8"))
            # Print the order details
            app_logger.info("Order details: %s", order_details["order"])
            app_logger.info('Order status: %s', order_details["order"]["status"])

            # Check if the "order" key exists in the order_details dictionary
            if "order" in order_details and "status" in order_details["order"]:
                # Print the order status
                app_logger.info("Order status: %s", order_details["order"]["status"])

                # Check if the order status is FILLED
                if order_details["order"]["status"] == "FILLED":
                    app_logger.info("Order filled successfully: %s", order_details)
                    return order_details
                else:
                    # If the order is not filled yet, wait for a few seconds and check again
                    time.sleep(5)
                    retries -= 1
            else:
                # If the "status" key is not found, log the information and retry
                app_logger.info(f"Order status not found. Retries remaining: {retries}")
                time.sleep(5)
                retries -= 1

        # If all retries fail, log an error and return None
        error_logger.error("All retries failed to fetch 'FILLED' order status.")
        return None

    except Exception as e:
        error_logger.error(f"An error occurred in wait_for_order: {e}")
        return None

wait_for_order(api_key, api_secret, order_id)