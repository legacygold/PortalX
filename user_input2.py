# user_input2.py
from logging_config import info_logger

def collect_user_input():
    print("User input function called")
    
    # Prompt the user for input
    base_asset = input("Enter the base asset (the symbol of the first asset in the trading pairing):")
    quote_asset = input("Enter the quote asset (the symbol of the second asset in the trading pairing):")
    product_id = input("Enter the product ID: ")
    starting_size_B = float(input("Enter the starting size of the base currency to trade with: "))
    starting_size_Q = float(input("Enter the starting size of the quote currency to trade with: "))
    profit_percent = float(input("Enter the desired profit percentage for each cycle: "))
    taker_fee = float(input("Enter the taker fee for your pricing tier on Coinbase Advanced Trade: "))
    maker_fee = float(input("Enter the maker fee for your pricing tier on Coinbase Advanced Trade: "))
    compound_percent = float(input("Enter the desired compounding percentage: "))
    compounding_option = input("Enter the compounding option (e.g., '100' for full compounding, 'partial' for partial compounding): ")
    wait_period_unit = input("Enter units for wait period interval ('minutes', 'hours', 'days'): ")
    first_order_wait_period = int(input("Enter the wait period interval in {} for the first order: ".format(wait_period_unit)))

    # Administrator: Enter Bollinger band calculation parameters
    chart_interval = int(input("Enter the chart interval in seconds (e.g., 60 for a 1-minute chart): "))
    num_intervals = int(input("Enter the number of intervals you want to fetch: "))
    window_size = int(input("Enter the window size for calculating Bollinger Bands: "))
    stacking = input("Enter 'True' or 'False' for whether to place multiple stacked price orders:")
    step_price = input("Enter 'True' or 'False' for whether to step up or down order prices based on market fluctuations:" )

    # Store the inputs in a configuration dictionary
    user_config = {
        "base_asset": base_asset,
        "quote_asset": quote_asset,
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
        "stacking": stacking,
        "step_price": step_price,
    }

    # Return the user configuration dictionary
    return user_config

def collect_sell_buy_input():
    print("Sell Buy Cycle Set Input")
    base_asset = input("Enter the base asset (the symbol of the first asset in the trading pairing):")
    quote_asset = input("Enter the quote asset (the symbol of the second asset in the trading pairing):")
    product_id = input("Enter the product ID: ")
    starting_size_B = float(input("Enter the starting size of the base currency to trade with: "))
    profit_percent = float(input("Enter the desired profit percentage for each cycle: "))
    taker_fee = float(input("Enter the taker fee for your pricing tier on Coinbase Advanced Trade: "))
    maker_fee = float(input("Enter the maker fee for your pricing tier on Coinbase Advanced Trade: "))
    compound_percent = float(input("Enter the desired compounding percentage: "))
    compounding_option = input("Enter the compounding option (e.g., '100' for full compounding, 'partial' for partial compounding): ")
    wait_period_unit = input("Enter units for wait period interval ('minutes', 'hours', 'days'): ")
    first_order_wait_period = int(input("Enter the wait period interval in {} for the first order: ".format(wait_period_unit)))
    
    user_config = {
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "product_id": product_id,
        "starting_size_B": starting_size_B,
        "starting_size_Q": 0,  # Placeholder for 'buy_sell' specific parameter
        "profit_percent": profit_percent,
        "taker_fee": taker_fee,
        "maker_fee": maker_fee,
        "compound_percent": compound_percent,
        "compounding_option": compounding_option,
        "wait_period_unit": wait_period_unit,
        "first_order_wait_period": first_order_wait_period,
    }

    return user_config

def collect_buy_sell_input():
    print("Buy Sell Cycle Set Input")
    base_asset = input("Enter the base asset (the symbol of the first asset in the trading pairing):")
    quote_asset = input("Enter the quote asset (the symbol of the second asset in the trading pairing):")
    product_id = input("Enter the product ID: ")
    starting_size_Q = float(input("Enter the starting size of the quote currency to trade with: "))
    profit_percent = float(input("Enter the desired profit percentage for each cycle: "))
    taker_fee = float(input("Enter the taker fee for your pricing tier on Coinbase Advanced Trade: "))
    maker_fee = float(input("Enter the maker fee for your pricing tier on Coinbase Advanced Trade: "))
    compound_percent = float(input("Enter the desired compounding percentage: "))
    compounding_option = input("Enter the compounding option (e.g., '100' for full compounding, 'partial' for partial compounding): ")
    wait_period_unit = input("Enter units for wait period interval ('minutes', 'hours', 'days'): ")
    first_order_wait_period = int(input("Enter the wait period interval in {} for the first order: ".format(wait_period_unit)))
    
    user_config = {
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "product_id": product_id,
        "starting_size_B": 0,  # Placeholder for 'sell_buy' specific parameter
        "starting_size_Q": starting_size_Q,
        "profit_percent": profit_percent,
        "taker_fee": taker_fee,
        "maker_fee": maker_fee,
        "compound_percent": compound_percent,
        "compounding_option": compounding_option,
        "wait_period_unit": wait_period_unit,
        "first_order_wait_period": first_order_wait_period,
    }

    return user_config

def get_valid_choice(prompt, valid_choices):
    while True:
        user_input = input(prompt)

        if user_input.isdigit() and int(user_input) in valid_choices:
            return int(user_input)
        else:
            print("Invalid input. Please enter a valid choice.")

# Indicate that user_input2.py module loaded successfully
info_logger.info("user_input2 module loaded successfully")
