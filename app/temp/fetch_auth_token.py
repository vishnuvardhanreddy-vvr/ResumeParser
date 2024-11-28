import time
import jwt
import logging
import os
from datetime import datetime, timedelta, timezone

# Declare the global variable
api_auth_token = None



def generate_jwt():
    global api_auth_token  # Declare that we want to modify the global variable

    private_key = os.getenv("private-key")  # Fetch the private key from environment variables

    current_utc_time = datetime.now(timezone.utc)

    # Define expiration time (1 hour from now)
    expiration_time = current_utc_time + timedelta(hours=int(os.getenv("TOKEN_EXPIRY_TIME")))


    # Define the payload (include user-specific data and any other claims you need)
    payload = {
        'user_id': os.getenv("user-id"),
        'extension_Roles': os.getenv("extension-roles"),
        'exp': expiration_time  # Expiration time for the JWT
    }
    
    # Sign the JWT using RS256 algorithm and the private key
    encoded_jwt = jwt.encode(payload, private_key, algorithm='RS256')
    
    # Update the global variable
    api_auth_token = encoded_jwt
    
    logging.info(f"Generated new JWT token with expiration time: {expiration_time}")

    return api_auth_token


def is_token_expired(token):
    try:
        # Decode the token without verifying the signature
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded_token.get('exp')

        # Check if the expiration time is in the past
        current_timestamp = int(time.time())
        if exp_timestamp and current_timestamp >= exp_timestamp:
            logging.info("API Token has expired.")
            return True  # Token has expired
        else:
            logging.info("API Token is still valid.")
            return False  # Token is still valid

    except jwt.ExpiredSignatureError:
        logging.warning("API Token signature expired.")
        return True  # If the signature is expired
    except jwt.DecodeError:
        logging.error("API Failed to decode JWT token.")
        return True  # If the token cannot be decoded

# Function to get the token, refreshing it if expired
def get_or_refresh_token():
    global api_auth_token

    # If no token exists or it has expired, generate a new one
    if not api_auth_token or is_token_expired(api_auth_token):
        logging.info("API Token is either missing or expired, refreshing token...")
        api_auth_token = generate_jwt()  # Refresh the token
    else:
        logging.info("Using existing valid API token.")

    return api_auth_token
