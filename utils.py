"""Utility functions"""
import os

from dotenv import load_dotenv


def load_env_vars():
    """Load environment variables from OS or .env file"""
    for i in range(0, 2):
        # Try to load OS environment variables
        if i == 0:
            etherscan_api_key = os.environ.get("ETHERSCAN_API_KEY")
            gsheet_file = os.environ.get("GSHEET_FILE")

            gsheet_credentials = {
                "type": "service_account",
                "project_id": os.environ.get("GSHEET_PROJECT_ID"),
                "private_key_id": os.environ.get("GSHEET_PRIVATE_KEY_ID"),
                "private_key": os.environ.get("GSHEET_PRIVATE_KEY"),
                "client_email": os.environ.get("GSHEET_CLIENT_EMAIL"),
                "client_id": os.environ.get("GSHEET_CLIENT_ID"),
            }

            if any(
                [
                    etherscan_api_key,
                    gsheet_file,
                    all(value == 0 for value in gsheet_credentials.values()),
                ]
            ):
                print(etherscan_api_key)
                print(gsheet_file)
                print(gsheet_credentials)
                return etherscan_api_key, gsheet_credentials, gsheet_file
            else:
                print("No OS environment variables found. Trying with .env file")
                continue

        elif i == 1:
            # Try to load .env file
            load_dotenv()
            etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
            gsheet_file = os.getenv("GSHEET_FILE")

            gsheet_credentials = {
                "type": "service_account",
                "project_id": os.getenv("GSHEET_PROJECT_ID"),
                "private_key_id": os.getenv("GSHEET_PRIVATE_KEY_ID"),
                "private_key": os.getenv("GSHEET_PRIVATE_KEY"),
                "client_email": os.getenv("GSHEET_CLIENT_EMAIL"),
                "client_id": os.getenv("GSHEET_CLIENT_ID"),
            }

            if any(
                [
                    etherscan_api_key,
                    gsheet_file,
                    all(value == 0 for value in gsheet_credentials.values()),
                ]
            ):
                return etherscan_api_key, gsheet_credentials, gsheet_file
            else:
                print("No valid .env file — using default settings. (CSV export only)")
                etherscan_api_key = False
                gsheet_credentials = False
                gsheet_file = False
                return etherscan_api_key, gsheet_credentials, gsheet_file
