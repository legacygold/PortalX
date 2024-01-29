# main2.py A sell_buy trading program
from logging_config import app_logger, info_logger, error_logger
import threading
import time
from user_input2 import collect_user_input, get_valid_choice
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


first_cycle = True

# Create a lock for user input
user_input_lock = threading.Lock()

def user_input_thread(collect_user_input):
    global first_cycle

    while True:
        if first_cycle:
            info_logger.info("First cycle: %s", first_cycle)
            first_cycle = False
        else:
            # Acquire the user input lock
            with user_input_lock:
                user_input = input("Type 'yes' to enter data for new cycle sets (or type 'exit' to quit): ")
            
            if user_input == 'exit':
                info_logger.info("user_input: %s", user_input)
                break
            elif user_input == 'yes':
                collect_user_input()

# Define locks
sell_buy_lock = threading.Lock()

# Initialize the counters for CycleSet instances
sell_buy_cycle_set_counter = 0

# Create a list to hold CycleSet instances
cycle_sets = []

def create_and_start_cycle_set_sell_buy(user_config):
    global sell_buy_cycle_set_counter

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
        new_cycle_set_sell_buy.cycleset_running = True
        cycle_sets.append(new_cycle_set_sell_buy)
        sell_buy_cycle_set_counter += 1

        # Create a Cycle instance and pass the parent CycleSet
        new_cycle_sell_buy = Cycle(
            "sell_buy",  # Cycle type
            new_cycle_set_sell_buy
        )

        new_cycle_set_sell_buy.cycle_instances.append(new_cycle_sell_buy)
        new_cycle_set_sell_buy.start_sell_buy_starting_cycle(user_config)

        with sell_buy_lock:
            app_logger.info(f"Cycle Set {sell_buy_cycle_set_counter} (sell_buy) created.")
            return new_cycle_set_sell_buy  # Return the newly created CycleSet
    else:
        error_logger.error("Sell-Buy cycle set not created. 'starting_size_B' is missing in user_config.")



def create_and_start_cycle_sets(user_config):
    if user_config:
                # Acquire the lock to ensure safe access to user_config
                user_config_lock.acquire()
                try:
                    # Create threads for each CycleSet instance
                    thread_sell_buy = threading.Thread(target=create_and_start_cycle_set_sell_buy, args=(user_config,))
                    
                    # Start the threads
                    thread_sell_buy.start()
                finally:
                    # Release the lock to allow other threads to use user_config
                    user_config_lock.release()
    else:
        error_logger.error("Unable to create cycle set(s). Invalid user input.")

menu_lock = threading.Lock()

# Define your main loop
def main_loop(interval_seconds, user_config):
    while True:
        try:
            # Check if there is new user input
            if user_config:
                # Acquire the lock to ensure safe access to user_config
                user_config_lock.acquire()
                try:
                    # Create threads for each CycleSet instance
                    thread_sell_buy = threading.Thread(target=create_and_start_cycle_set_sell_buy, args=(user_config,))
                    
                    # Start the threads
                    thread_sell_buy.start()
                finally:
                    # Release the lock to allow other threads to use user_config
                    user_config_lock.release()

            else:
                error_logger.error("Unable to create cycle set(s). Invalid user input.")

            choice = None  # Reset 'choice' at the beginning of each iteration
            
            # Start, monitor, and manage the existing cycle sets
            for cycle_set in cycle_sets:
                if any(cycle_set.cycleset_is_running() for cycle_set in cycle_sets):
                    # Handle completed cycle sets, e.g., logging, reporting, or re-creating               
                    with menu_lock:
                        # Provide options to monitor and manage CycleSets
                        print("Options:")
                        print("1. Start new cycle set(s)?")
                        print("2. Monitor CycleSets")
                        print("3. Stop a CycleSet")
                        print("4. Exit")

                        # Display options and get the user's choice
                        choice = get_valid_choice("Enter the number of your choice: ", ["1", "2", "3", "4"])

                if choice == 1:
                    # Run user_input2.py to input user data (or create a function "collect_user_input()" to do this)
                    user_config = collect_user_input()
                    # Create a new instance of the CycleSet class and start first cycle
                    create_and_start_cycle_sets(user_config)

                elif choice == 2:
                    # Display information about each CycleSet
                    for i, cycle_set in enumerate(cycle_sets, start=1):
                        print("Check info.log for info")
                        info_logger.info(f"Cycle Set {i}: {cycle_set.get_status()}")
                    
                elif choice == 3:
                    # User wants to stop a CycleSet instance
                    # Ask the user for the cycle set number they want to stop
                    cycle_set_number = int(input("Enter the cycle set number you want to stop: "))

                    # Check if the provided cycle set number is valid
                    if 1 <= cycle_set_number <= len(cycle_sets):
                        # Stop the selected CycleSet
                        cycle_sets[cycle_set_number - 1].stop()
                        app_logger.info(f"CycleSet {cycle_set_number} has been stopped.")
                    else:
                        error_logger.error("Invalid cycle number. Please enter a valid cycle number.")

                elif choice == 4:
                    # Exit the program
                    print("PortalX sell_buy program exited...")
                    break

            # Sleep for a while before checking again to avoid excessive CPU usage
            time.sleep(interval_seconds)

        except Exception as e:
            # Handle exceptions or errors
            error_logger.error(f"An error occurred in the main loop: {e}")
            # You can choose to continue or break the loop based on your error handling strategy

# Start the main loop
if __name__ == "__main__":
    interval_seconds = 10 # Define your desired interval

    print("Starting the user input thread")
    # Create a thread for user input with the collect_user_input function as an argument
    user_input_thread = threading.Thread(target=user_input_thread, args=(collect_user_input,))
    user_input_thread.daemon = True  # Daemonize the thread so it doesn't block program exit
    user_input_thread.start()

    main_loop(interval_seconds, user_config)
