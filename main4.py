# main.py
from logging_config import app_logger, error_logger
from starting_input import user_config
from trading_record_manager import create_and_start_cycle_sets

if __name__ == "__main__":
    try:

        # Create a new instance of the CycleSet class and start first cycle
        app_logger.info("Creating and starting cycle set(s)...")
        create_and_start_cycle_sets(user_config)

    except Exception as e:
        # Handle exceptions or errors
        error_logger.error(f"An error occurred in the main loop: {e}")
        # You can choose to continue or break the loop based on your error handling strategy
