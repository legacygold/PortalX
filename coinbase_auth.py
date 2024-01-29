#coinbase_auth.py
import http.client
import hmac
import hashlib
import time
import json
import requests
from config import config_data
from logging_config import app_logger, info_logger, error_logger

# API credentials
api_key = config_data["api_key"]
api_secret = config_data["api_secret"]

# OAuth2 Configuration Constants
COINBASE_OAUTH_URL = 'https://www.coinbase.com/oauth/authorize'
COINBASE_TOKEN_URL = 'https://api.coinbase.com/oauth/token'
CLIENT_ID = 'your-client-id'  # Replace with your actual client ID
CLIENT_SECRET = 'your-client-secret'  # Replace with your actual client secret
REDIRECT_URI = 'http://localhost:8080/callback'  # Replace with your actual redirect URI

def create_signed_request(api_key, api_secret, method, endpoint, body= ''):
    if api_key is None or api_secret is None:
        error_logger.error("Error: API key and/or API secret is missing.")
        return None
    
    timestamp = str(int(time.time()))
    payload = timestamp + method + endpoint + body
    signature = hmac.new(api_secret.encode('utf-8'), payload.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'CB-ACCESS-KEY': api_key,
        'CB-ACCESS-SIGN': signature,
        'CB-ACCESS-TIMESTAMP': timestamp,
        'User-Agent': 'PortalX_Trading_Bot',
    }
    
    return headers

# Function to fetch historical data
def fetch_historical_data(product_id, chart_interval, num_intervals):
    
    conn = http.client.HTTPSConnection("api.exchange.coinbase.com")
    
    # Create headers with the User-Agent header
    headers = {
        'User-Agent': 'PortalX_Trading_Bot',  # Replace with your application's name
    }
    
    # Calculate start and end times
    end_time = int(time.time())
    start_time = end_time - (chart_interval * num_intervals)
    
    # Construct the URL with query parameters
    url = f"/products/{product_id}/candles?granularity={chart_interval}&start={start_time}&end={end_time}"
    
    # Fetch historical data
    conn.request("GET", url, headers=headers)
    res = conn.getresponse()
    data = res.read()
    
    if res.status == 200:
        historical_data = json.loads(data.decode("utf-8"))
        return historical_data
    else:
        error_logger.error(f"Error fetching historical data: {res.status} {res.reason}")
        return None

# Function to generate the OAuth2 authorization URL
def generate_oauth_authorization_url():
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        # You can add more optional parameters here if needed
    }
    authorization_url = f'{COINBASE_OAUTH_URL}?{"&".join([f"{k}={v}" for k, v in params.items()])}'
    info_logger.info("OAuth2 url generated successfully")
    return authorization_url

# Function to exchange the authorization code for an access token
def exchange_code_for_access_token(authorization_code):
    data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
    }
    response = requests.post(COINBASE_TOKEN_URL, data=data)
    if response.status_code == 200:
        info_logger.info("Authorization code successfully exchanged for access token")
        return response.json()
    else:
        return None

# Print a message indicating successful module loading
info_logger.info("coinbase_auth module loaded successfully")







