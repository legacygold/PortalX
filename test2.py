# test2.py
import logging
import threading
from logging_config import app_logger, error_logger
from starting_input import user_config
from cycle_set_utils import CycleSet, Cycle  # Import the original CycleSet class

# Set up logging as you did in 'logging_config.py'
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)

# Create a StreamHandler to print log messages to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
app_logger.addHandler(console_handler)

# Define locks
sell_buy_lock = threading.Lock()
buy_sell_lock = threading.Lock()

# Initialize the counters for CycleSet instances
sell_buy_cycle_set_counter = 0
buy_sell_cycle_set_counter = 0

# Create a list to hold CycleSet instances
cycle_sets = []

def create_and_start_cycle_set_sell_buy(user_config):
    with sell_buy_lock:
        global sell_buy_cycle_set_counter
        sell_buy_cycle_set_counter += 1

        if "starting_size_B" in user_config:
            # Create one sell-buy cycle set instance
            starting_size = user_config["starting_size_B"]
            cycle_type = "sell-buy"
            new_cycle_set_sell_buy = CycleSet(
                user_config["product_id"],
                starting_size,
                user_config["profit_percent"],
                user_config["taker_fee"],
                user_config["maker_fee"],
                user_config["compound_percent"],
                user_config["compounding_option"],
                user_config["wait_period_unit"],
                user_config["first_order_wait_period"],
                user_config["chart_interval"],
                user_config["num_intervals"],
                user_config["window_size"],
                user_config["stacking"],
                user_config["step_price"],
                cycle_type=cycle_type
            )
            cycle_sets.append(new_cycle_set_sell_buy)

            # Create a Cycle instance and pass the parent CycleSet
            new_cycle_sell_buy = Cycle(
                "sell_buy",  # Cycle type
                user_config['product_id'],
                user_config['starting_size_B'],
                user_config['profit_percent'],
                user_config['taker_fee'],
                user_config['maker_fee'],
                user_config["compound_percent"],
                user_config["compounding_option"],
                user_config["wait_period_unit"],
                user_config["first_order_wait_period"],
                user_config["chart_interval"],
                user_config["num_intervals"],
                user_config["window_size"],
                user_config["stacking"],
                user_config["step_price"],
                new_cycle_set_sell_buy
            )

            new_cycle_set_sell_buy.cycle_instances.append(new_cycle_sell_buy)
            new_cycle_set_sell_buy.start_sell_buy_starting_cycle(user_config)       
            app_logger.info(f"Cycle Set {sell_buy_cycle_set_counter} (sell_buy) created.")
            return new_cycle_set_sell_buy  # Return the newly created CycleSet
        else:
            error_logger.error("Sell-Buy cycle set not created. 'starting_size_B' is missing in user_config.")

def create_and_start_cycle_set_buy_sell(user_config):
    with buy_sell_lock:
        global buy_sell_cycle_set_counter
        buy_sell_cycle_set_counter += 1

        if "starting_size_Q" in user_config:
            # Create one buy-sell cycle set instance
            starting_size = user_config["starting_size_Q"]
            cycle_type = "buy-sell"
            new_cycle_set_buy_sell = CycleSet(
                user_config["product_id"],
                starting_size,
                user_config["profit_percent"],
                user_config["taker_fee"],
                user_config["maker_fee"],
                user_config["compound_percent"],
                user_config["compounding_option"],
                user_config["wait_period_unit"],
                user_config["first_order_wait_period"],
                user_config["chart_interval"],
                user_config["num_intervals"],
                user_config["window_size"],
                user_config["stacking"],
                user_config["step_price"],
                cycle_type=cycle_type
            )
            cycle_sets.append(new_cycle_set_buy_sell)

            # Create a Cycle instance and pass the parent CycleSet
            new_cycle_buy_sell = Cycle(
                "buy_sell",  # Cycle type
                user_config['product_id'],
                user_config['starting_size_Q'],
                user_config['profit_percent'],
                user_config['taker_fee'],
                user_config['maker_fee'],
                user_config["compound_percent"],
                user_config["compounding_option"],
                user_config["wait_period_unit"],
                user_config["first_order_wait_period"],
                user_config["chart_interval"],
                user_config["num_intervals"],
                user_config["window_size"],
                user_config["stacking"],
                user_config["step_price"],
                new_cycle_set_buy_sell
            )

            new_cycle_set_buy_sell.cycle_instances.append(new_cycle_buy_sell)
            new_cycle_set_buy_sell.start_buy_sell_starting_cycle(user_config)
            app_logger.info(f"Cycle Set {buy_sell_cycle_set_counter} (buy_sell) created.")
            return new_cycle_set_buy_sell  # Return the newly created CycleSet

        else:
            error_logger.error("Buy-Sell cycle set not created. 'starting_size_Q' is missing in user_config.")

# For testing purposes, you can call these functions here
if __name__ == "__main__":
    # Use the user_config imported from starting_input
    create_and_start_cycle_set_sell_buy(user_config)
    create_and_start_cycle_set_buy_sell(user_config)



