# logging_config.py

import logging

# Create a logger for errors
error_logger = logging.getLogger('errors')
error_logger.setLevel(logging.ERROR)

# Create a file handler for error messages
error_handler = logging.FileHandler('error.log')
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)

# Log an error message
error_logger.error("This is an error message")

# Create a logger for general info
info_logger = logging.getLogger('info')
info_logger.setLevel(logging.INFO)

# Create a file handler for info messages
info_handler = logging.FileHandler('info.log')
info_handler.setLevel(logging.INFO)
info_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
info_handler.setFormatter(info_formatter)
info_logger.addHandler(info_handler)

# Log an info message
info_logger.info("This is an info message")

# Create a logger for statements that will be both logged and printed
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.INFO)

# Create a file handler for "app.log"
app_handler = logging.FileHandler('app.log')

# Create a formatter for the messages in "app.log"
app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)

# Create a StreamHandler to print log messages to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Add both handlers to the "app" logger
app_logger.addHandler(app_handler)
app_logger.addHandler(console_handler)

# Now, you can use app_logger.info() to log messages to 'app.log' and print them to the console.
app_logger.info("This message will be logged in 'app.log' and printed to the console.")