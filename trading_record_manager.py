# trading_record_manager.py
import sys
import threading
import http.client
import time
from logging_config import app_logger, info_logger, error_logger
from user_input2 import collect_user_input, get_valid_choice
from starting_input import user_config
from config import config_data
from cycle_set_utils import CycleSet, Cycle
        
conn = http.client.HTTPSConnection("api.coinbase.com")

api_key = config_data["api_key"]
api_secret = config_data["api_secret"]

# Define a list to store cycle set instances
cycle_sets_instances = []

# Define a dictionary to store additional data about each cycle set
cycle_sets_data = {}

# Example structure for additional data
# Each cycle set ID will map to a dictionary containing relevant information
# This is just a placeholder structure; you can customize it based on your needs
# For simplicity, I'm using cycle set IDs as integers, you can adjust it based on your actual IDs
cycle_sets_data = {
    1: {
        'completed_cycles': 5,
        'starting_dollar_value': 1000,
        'current_dollar_value': 1200,
        'percent_gain_loss_dollar_value': 20,
        'percent_gain_loss_base_asset': 15,
        'percent_gain_loss_quote_asset': 25,
        'average_profit_percent_per_cycle': 2,
        'average_profit_percent_per_day': 0.5,
    },
    2: {
        # ... data for cycle set 2
    },
    # ... additional cycle sets
}

# Define a list to store cycle set instances
cycle_instances = []

# Define a dictionary to store additional data about each cycle set
cycle_data = {}

# Example structure for additional data
# Each cycle set ID will map to a dictionary containing relevant information
# This is just a placeholder structure; you can customize it based on your needs
# For simplicity, I'm using cycle set IDs as integers, you can adjust it based on your actual IDs
cycle_data = {
    1: {
        'completed_cycle_number': 1,
        'cycleset_number': 1,
        'starting_dollar_value': 1000,
        'current_dollar_value': 1200,
        'percent_gain_loss_dollar_value': 20,
        'percent_gain_loss_base_asset': 15,
        'percent_gain_loss_quote_asset': 25,
        'average_profit_percent_per_cycle': 2,
        'average_profit_percent_per_day': 0.5,
    },
    2: {
        # ... data for cycle set 2
    },
    # ... additional cycle sets
}

class TradingRecordManager:
    def __init__(self):
        # Initialize attributes to store cycle set instances and data
        self.cycle_sets_instances = []
        self.cycle_sets_data = {}

    def add_cycle_set(self, cycle_set):
        # Add a new cycle set instance
        self.cycle_sets_instances.append(cycle_set)

        # Add initial data for the cycle set (you might want to adjust this based on your CycleSet attributes)
        self.cycle_sets_data[cycle_set.id] = {
            'cycle_set_number': 0,
            'instance_id': '',
            'product_id': '',
            'starting_size': 0,
            'profit_percent': 0,
            'taker_fee': 0,
            'maker_fee': 0,
            'compound_percent': 0,
            'compounding_option': '',
            'wait_period_unit': '',
            'first_order_wait_period': 0,
            'chart_interval': 0,
            'num_intervals': 0,
            'window_Size': 0,
            'stacking': None,
            'step_price': None,
            'cycle_type': '',
            'orders': [],
            'cycle_instances': [],
            'cycle_set_running': None,
            'cycleset_status': '',
            'completed_cycles': 0,
            'starting_dollar_value': 0,
            'current_dollar_value': 0,
            'percent_gain_loss_dollar': 0,
            'percent_gain_loss_base': 0,
            'percent_gain_loss_quote': 0,
            'average_profit_percent_per_hour': 0,
            'average_profit_percent_per_day': 0
        }

    def add_cycle(self, cycleset_instance_id, cycle):
        # Add a new cycle to a specific cycle set
        self.cycle_sets_instances[cycleset_instance_id].append(cycle)

        # Update data for the cycle set based on the completed cycle
        self.update_cycle_set_data(cycleset_instance_id)

    def update_cycle_set_data(self, cycleset_instance_id):
        # Perform calculations to update data for the cycle set
        # This might involve iterating through cycles in the cycle set and updating data accordingly
        # For simplicity, let's assume you have a method in CycleSet for getting the relevant data
        cycle_set = self.cycle_sets_instances[cycleset_instance_id]
        data = cycle_set.get_cycle_set_data()  # You need to implement this method in your CycleSet class
        # Update the data in the dictionary
        self.cycle_sets_data[cycleset_instance_id].update(data)

    def display_summary_data(self):
        # Display essential information for each cycle set
        for cycleset_instance_id, data in self.cycle_sets_data.items():
            print(f"{cycleset_instance_id}: {data['completed_cycles']} cycles, Starting Value: ${data['starting_dollar_value']}")

    def display_detailed_data(self):
        # Display detailed information for each cycle set
        for cycleset_instance_id, data in self.cycle_sets_data.items():
            print(f"Cycle Set {cycleset_instance_id}:")
            for key, value in data.items():
                print(f"  {key}: {value}")

    def display_order_details(self, order_id):
        from order_utils import get_order_details
        # Display order details of an order from a cycle of a cycle set
        for order_id, data in self.cycle_sets_data.orders.items():
            order_details = get_order_details(conn, api_key, api_secret, order_id, max_retries=5)
            app_logger.info(f"Order {order_id} details: {order_details}")

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
menu_lock = threading.Lock()

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

# Functions to display menu options when called
def menu_choice(prompt, timeout=60):
    start_time = time.time()
    user_input = None

    while True:
        try:
            user_input = input(prompt)

            if user_input.strip().lower() in {'y', 'n'}:
                break

            print("Invalid input. Please enter 'y' or 'n'.")
        except KeyboardInterrupt:
            print("Interrupted by user. Exiting...")
            exit(0)

        if time.time() - start_time > timeout:
            print(f"No response received within {timeout} seconds. Assuming 'n'.")
            user_input = 'n'
            break

    return user_input.strip().lower()


def display_options_menu():
        print("Options:")
        print("1. Start new cycle set(s)?")
        print("2. Monitor CycleSets")
        print("3. Stop a CycleSet")
        print("4. Exit")
        return get_valid_choice("Enter the number of your choice: ", [1, 2, 3, 4])

# Define function to handle calling the 'Options menu'
def handle_options_menu():
    with menu_lock:
        # Define options menu event
        options_menu_event = threading.Event()

    while True:
        try:
            with menu_lock:
                # Set options_menu_event
                options_menu_event.set()

                if options_menu_event.is_set():
                    try:   
                        menu_prompt = menu_choice("Do you want to display the Options Menu? (y/n): ", timeout=60)
                        
                        # Clear the event after handling it
                        options_menu_event.clear()
                    
                    except Exception as e:
                        print(f"Exception during menu_choice: {e}")
                else:
                    # Indicate Options menu event is not set
                    error_logger.error("Unable to access 'Options menu' because an event was not set")

            if menu_prompt == 'y':
                
                # Display options and get the user's choice
                choice = display_options_menu()

                if choice == 1:

                    # Run user_input2.py to input user data (or create a function "collect_user_input()" to do this)
                    user_config = collect_user_input()
                    # Create a new instance of the CycleSet class and start first cycle
                    create_and_start_cycle_sets(user_config)

                elif choice == 2:
                    # Display information about each CycleSet

                    # Create separate lists for 'sell_buy' and 'buy_sell' cycle sets
                    sell_buy_cycle_sets_data = []
                    buy_sell_cycle_sets_data = []

                    for i, cycle_set in enumerate(cycle_sets, start=1):
                        # Collect cycle set data
                        cycle_set_data = {
                            'cycle_set_number': cycle_set.cycleset_number,
                            'cycleset_instance_id': cycle_set.cycleset_instance_id,
                            'cycle_set_type': cycle_set.cycle_type,
                            'cycleset_status': cycle_set.cycleset_status,
                            'completed_cycles': cycle_set.completed_cycles,
                            'product_id': cycle_set.product_id,
                            'starting_size': cycle_set.starting_size,
                            'profit_percent': cycle_set.profit_percent,
                            'taker_fee': cycle_set.taker_fee,
                            'maker_fee': cycle_set.maker_fee,
                            'compound_percent': cycle_set.compound_percent,
                            'compounding_option': cycle_set.compounding_option,
                            'wait_period_unit': cycle_set.wait_period_unit,
                            'first_order_wait_period': cycle_set.first_order_wait_period,
                            'chart_interval': cycle_set.chart_interval,
                            'num_intervals': cycle_set.num_intervals,
                            'window_Size': cycle_set.window_size,
                            'stacking': cycle_set.stacking,
                            'step_price': cycle_set.step_price, 
                            'cycleset_running': cycle_set.cycleset_running,
                            'starting_dollar_value': cycle_set.starting_dollar_value,
                            'current_dollar_value': cycle_set.current_dollar_value,
                            'percent_gain_loss_dollar': cycle_set.percent_gain_loss_dollar,
                            'percent_gain_loss_base': cycle_set.percent_gain_loss_base,
                            'percent_gain_loss_quote': cycle_set.percent_gain_loss_quote,
                            'average_profit_percent_per_hour': cycle_set.average_profit_percent_per_hour,
                            'average_profit_percent_per_day': cycle_set.average_profit_percent_per_day,
                            'cycle_instances': [{
                                'cycle_number': cycle.cycle_number,
                                'open_size': cycle.open_size,
                                'cycleset_instance_id': cycle.cycleset_instance_id,
                                'cycle_type': cycle.cycle_type,
                                'cycle_instance_id': cycle.cycle_instance_id,
                                'cycle_running': cycle.cycle_running,
                                'cycle_status': cycle.cycle_status,
                                'orders': cycle.orders,
                                # Include other relevant cycle attributes here
                            } for cycle in cycle_set.cycle_instances],                          
                        }

                        # Determine the target list based on cycle set type
                        target_list = sell_buy_cycle_sets_data if cycle_set.cycle_type == 'sell_buy' else buy_sell_cycle_sets_data
                        target_list.append(cycle_set_data)

                    # Print the 'sell_buy' cycle sets data
                    print("Sell-Buy Cycle Sets:")
                    for data in sell_buy_cycle_sets_data:
                        print(data)

                    # Print the 'buy_sell' cycle sets data
                    print("Buy-Sell Cycle Sets:")
                    for data in buy_sell_cycle_sets_data:
                        print(data)
                                    
                elif choice == 3:
                    # User wants to stop a CycleSet instance

                    # Filter running cycle sets
                    running_cycle_sets = [cycle_set for cycle_set in cycle_sets if cycle_set.cycleset_running]

                    if running_cycle_sets:
                        # Display a numbered list of running cycle sets
                        print("Running Cycle Sets:")
                        for i, cycle_set in enumerate(running_cycle_sets, start=1):
                            print(f"{i}. {cycle_set.cycleset_instance_id}")

                        # Ask the user for the number corresponding to the cycle set they want to stop
                        try:
                            choice_number = int(input("Enter the number of the cycle set you want to stop: "))
                            if 1 <= choice_number <= len(running_cycle_sets):
                                # Stop the selected CycleSet
                                selected_cycle_set = running_cycle_sets[choice_number - 1]
                                selected_cycle_set.stop()
                                app_logger.info(f"CycleSet {selected_cycle_set.cycleset_instance_id} has been stopped.")
                            else:
                                error_logger.error("Invalid number. Please enter a valid number.")
                        except ValueError:
                            error_logger.error("Invalid input. Please enter a valid number.")
                    else:
                        print("No running cycle sets to stop.")

                elif choice == 4:
                    # Exit the program
                    print("Exiting Portal-X...")
                    sys.exit()

                # Release the lock to allow other threads to use user_config
                options_menu_event.clear()

            if menu_prompt == 'n':
                return
            
        except Exception as e:
            # Handle exceptions or errors
            error_logger.error(f"An error occurred in the main loop: {e}")
            # You can choose to continue or break the loop based on your error handling strategy