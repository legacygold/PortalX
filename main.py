# main.py
from logging_config import app_logger, info_logger, error_logger
import threading
from starting_input import user_config
from cycle_set_utils import CycleSet, Cycle  # Import the original CycleSet class

# Configure the logging settings in your script

# Use error_logger for error messages
error_logger.error("This is an error message")

# Use info_logger for general info
info_logger.info("This is an info message")

# Use app_logger for statements that will be both logged and printed
app_logger.info("This message will be logged in 'app.log' and printed to the console.")

# Create a lock to prevent concurrent modification of user_config
user_config_lock = threading.Lock()

info_logger.info("user_config data: %s", user_config)

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
        try:
            if "starting_size_B" in user_config:
                # Create one sell-buy cycle set instance
                starting_size = user_config["starting_size_B"]
                cycle_type = "sell_buy"
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
                new_cycle_set_sell_buy.cycleset_running = True
                cycle_sets.append(new_cycle_set_sell_buy)
                sell_buy_cycle_set_counter += 1

                # Create a Cycle instance and pass the parent CycleSet
                new_cycle_sell_buy = Cycle(
                    starting_size,
                    new_cycle_set_sell_buy, 
                    "sell_buy",  # Cycle type
                )

                app_logger.info(f"Cycle Set {sell_buy_cycle_set_counter} (sell_buy) created.")

                new_cycle_set_sell_buy.cycle_instances.append(new_cycle_sell_buy)

                # Start the sell-buy cycle set
                new_cycle_set_sell_buy.start_sell_buy_starting_cycle(user_config, sell_buy_cycle_set_counter)
                
                return new_cycle_set_sell_buy  # Return the newly created CycleSet
            else:
                error_logger.error("Sell-Buy cycle set not created. 'starting_size_B' is missing in user_config.")

        except Exception as e:
            # Handle exceptions or errors
            error_logger.error(f"An error occurred in the main loop: {e}")

def create_and_start_cycle_set_buy_sell(user_config):
    with buy_sell_lock:
        global buy_sell_cycle_set_counter
        try:
            if "starting_size_Q" in user_config:
                # Create one buy-sell cycle set instance
                starting_size = user_config["starting_size_Q"]
                cycle_type = "buy_sell"
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
                new_cycle_set_buy_sell.cycleset_running = True
                cycle_sets.append(new_cycle_set_buy_sell)
                buy_sell_cycle_set_counter += 1

                # Create a Cycle instance and pass the parent CycleSet
                new_cycle_buy_sell = Cycle(
                    starting_size,
                    new_cycle_set_buy_sell,
                    "buy_sell" # Cycle type
                )

                app_logger.info(f"Cycle Set {buy_sell_cycle_set_counter} (buy_sell) created.")

                new_cycle_set_buy_sell.cycle_instances.append(new_cycle_buy_sell)

                # Start the sell-buy cycle set
                new_cycle_set_buy_sell.start_buy_sell_starting_cycle(user_config, buy_sell_cycle_set_counter)     
                
                return new_cycle_set_buy_sell  # Return the newly created CycleSet

            else:
                error_logger.error("Buy-Sell cycle set not created. 'starting_size_Q' is missing in user_config.")

        except Exception as e:
            # Handle exceptions or errors
            error_logger.error(f"An error occurred in the main loop: {e}")

def create_and_start_cycle_sets(user_config):
    if user_config:
        # Acquire the lock to ensure safe access to user_config
        with user_config_lock:
            try:
                # Create threads for each CycleSet instance
                if user_config["starting_size_B"] > 0 and user_config["starting_size_Q"] > 0:
                    thread_sell_buy = threading.Thread(target=create_and_start_cycle_set_sell_buy, args=(user_config,))
                    thread_buy_sell = threading.Thread(target=create_and_start_cycle_set_buy_sell, args=(user_config,))

                    # Start the threads
                    thread_sell_buy.start()
                    thread_buy_sell.start()

                elif user_config["starting_size_B"] > 0 and user_config["starting_size_Q"] == 0:
                    thread_sell_buy = threading.Thread(target=create_and_start_cycle_set_sell_buy, args=(user_config,))

                    # Start the thread
                    thread_sell_buy.start()

                elif user_config["starting_size_B"] == 0 and user_config["starting_size_Q"] > 0:
                    thread_buy_sell = threading.Thread(target=create_and_start_cycle_set_buy_sell, args=(user_config,))

                    # Start the threads
                    thread_buy_sell.start()

            except Exception as e:
                # Handle exceptions or errors
                error_logger.error(f"An error occurred in the main loop: {e}")

    else:
        error_logger.error("Unable to create cycle set(s). Invalid user input.")

# Define your main loop
def main_loop(user_config):
    while True:
        try:
            # Check if there is new user input
            if user_config:
                # Acquire the lock to ensure safe access to user_config
                with user_config_lock:
                    try:
                        # Create threads for each CycleSet instance
                        if user_config["starting_size_B"] > 0 and user_config["starting_size_Q"] > 0:
                            thread_sell_buy = threading.Thread(target=create_and_start_cycle_set_sell_buy, args=(user_config,))
                            thread_buy_sell = threading.Thread(target=create_and_start_cycle_set_buy_sell, args=(user_config,))

                            # Start the threads
                            thread_sell_buy.start()
                            thread_buy_sell.start()

                        elif user_config["starting_size_B"] > 0 and user_config["starting_size_Q"] == 0:
                            thread_sell_buy = threading.Thread(target=create_and_start_cycle_set_sell_buy, args=(user_config,))

                            # Start the thread
                            thread_sell_buy.start()

                        elif user_config["starting_size_B"] == 0 and user_config["starting_size_Q"] > 0:
                            thread_buy_sell = threading.Thread(target=create_and_start_cycle_set_buy_sell, args=(user_config,))

                            # Start the threads
                            thread_buy_sell.start()
 
                    except Exception as e:
                        # Handle exceptions or errors
                        error_logger.error(f"An error occurred in the main loop: {e}")
            else:
                error_logger.error("Unable to create cycle set(s). Invalid user input.")           

        except Exception as e:
            # Handle exceptions or errors
            error_logger.error(f"An error occurred in the main loop: {e}")
            # You can choose to continue or break the loop based on your error handling strategy

# Start the main loop
if __name__ == "__main__":

    main_loop(user_config)
