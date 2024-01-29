#user_input.py
from config import config_data
from logging_config import app_logger, info_logger

# Access API credentials and other configuration settings
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]

# Get user inputs and store them
product_id = "XLM-USD"
starting_size_B = 100  # Replace with the desired value of the base currency to trade with
starting_size_Q = 10  # Replace with the desired value of the quote currency to trade with
profit_percent = 0.01  # The desired profit percentage for each cycle
taker_fee = 0.008 # The taker fee for user's pricing tier on Coinbase Advanced Trade
maker_fee = 0.006 # The maker fee for user's pricing tier on Coinbase Advanced Trade
compound_percent = 100  # The desired compounding percentage
compounding_option = "100"  # "100" for full compounding, "partial" for partial compounding
wait_period_unit = "minutes" # Enter units for wait period interval ("minutes", "hours", "days")
first_order_wait_period = 5 # Enter amount in wait_period_units for interval for wait period

# Administrator: Enter Bollinger band calculation parameters
chart_interval = 60     # Replace with your desired chart interval in seconds (e.g., 60 for 1-minute chart): minimum 60, maximum 1,440
num_intervals = 20     # Replace with the number of intervals you want to fetch
window_size = 20        # Define the window size for calculating Bollinger Bands

# Store the inputs in a configuration file or Python object
user_config = {
    "product_id": product_id,
    "starting_size_B": starting_size_B,
    "starting_size_Q": starting_size_Q,
    "profit_percent": profit_percent,
    "taker_fee": taker_fee,
    "maker_fee": maker_fee,
    "compound_percent": compound_percent,
    "compounding_option": compounding_option,
    "wait_period_unit": wait_period_unit,
    "first_order_wait_period": first_order_wait_period,
    "chart_interval": chart_interval,
    "num_intervals": num_intervals,
    "window_size": window_size,
}

# Print user input data
app_logger.info("User Configuration: %s", user_config)

# Indicate that user_input.py module loaded successfully
info_logger.info("user_input module loaded successfully")
