# test_function.py
import threading
import time
from trading_record_manager import menu_choice, display_options_menu, menu_lock, collect_user_input, create_and_start_cycle_sets
from logging_config import app_logger, error_logger
from user_input2 import user_config
from cycle_set_utils import CycleSet, Cycle  # Import the original CycleSet class

# Define locks
sell_buy_lock = threading.Lock()
buy_sell_lock = threading.Lock()
print_lock = threading.Lock()
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
                new_cycle_set_sell_buy.start_sell_buy_starting_cycle(user_config)
                
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
                new_cycle_set_buy_sell.start_buy_sell_starting_cycle(user_config)     
                
                return new_cycle_set_buy_sell  # Return the newly created CycleSet

            else:
                error_logger.error("Buy-Sell cycle set not created. 'starting_size_Q' is missing in user_config.")

        except Exception as e:
            # Handle exceptions or errors
            error_logger.error(f"An error occurred in the main loop: {e}")

# Create an event
options_menu_event = threading.Event()

# Set options menu
options_menu_event.set()

def test_function():
    # Set the event
    options_menu_event.set()
    # Check if the event is set
    if options_menu_event.is_set():
        print("Options menu event is set.")
    else:
        print("Options menu event is not set.")

# Run the test function
test_function()

# Sleep to observe the state change
time.sleep(2)

# Clear the event
options_menu_event.clear()

# Check again
if options_menu_event.is_set():
    print("Options menu event is set.")
else:
    print("Options menu event is not set.")

# Re-set options menu
options_menu_event.set()

if options_menu_event.is_set():    
    # Choice for displaying options menu
    menu_prompt = menu_choice("Do you want to display the Options Menu? (y/n): ", ['y', 'n'])
    print(menu_prompt)

if menu_prompt == 'y':
    
    # Display options and get the user's choice
    choice = display_options_menu()
    print(choice)

    if choice == 1:
        with menu_lock:
            # Run user_input2.py to input user data (or create a function "collect_user_input()" to do this)
            user_config = collect_user_input()
            # Create a new instance of the CycleSet class and start first cycle
            create_and_start_cycle_sets(user_config)

    elif choice == 2:
        # Display information about each CycleSet
        with menu_lock:
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
                    'cycle_instances': [{
                        'cycle_number': cycle.cycle_number,
                        'open_size': cycle.open_size,
                        'cycleset_instance_id': cycle.cycleset_instance_id,
                        'cycle_type': cycle.cycle_type,
                        'cycle_instance_id': cycle.cycle_instance_id,
                        'cycle_running': cycle.self.cycle_running,
                        'cycle_status': cycle.cycle_status,
                        'orders': cycle.orders,
                        # Include other relevant cycle attributes here
                    } for cycle in cycle_set.cycle_instances],
                    'cycleset_running': cycle_set.cycleset_running,
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
        with menu_lock:
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
        print("PortalX exited...")

    # Release the lock to allow other threads to use user_config
    options_menu_event.clear()



