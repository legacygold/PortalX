# error_handling_utils.py
from threading import Lock
from logging_config import error_logger

# Initialize a lock for error handling
error_handling_lock = Lock()

def handle_error(error_message):
    with error_handling_lock:
        # You can log or print the error message here
        error_logger.error("Error: %s", error_message)

user_config = {}  # or user_config = None, depending on how you initialize it

def handle_error_and_return_to_main_loop(error_message):
    error_logger.error(f"Error: {error_message}")
    
    while True:
        user_input = input("Do you want to continue? (yes/no): ")
        
        if user_input.lower() == "yes":
            return  # Return to the main loop
        elif user_input.lower() == "no":
            exit(0)  # Exit the program
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

