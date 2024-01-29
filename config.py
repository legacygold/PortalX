#config.py
import json
from logging_config import info_logger, error_logger

def load_config(file_path):
    with open(file_path, "r") as json_file:
        config_data = json.load(json_file)
    return config_data

# Load the configuration settings from the JSON file
print("Loading API credentials...")
config_data = load_config("D:\\APIs\\CBAT_api_3.json")
# Check API credentials sent successfully
if config_data is not None:
    info_logger.info("API credentials fetched successfully")
else:
    error_logger.error("Failed to fetch API credentials. Please check the file path.")

# Indicate that config.py module loaded successfully
info_logger.info("config module loaded successfully")