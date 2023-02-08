"""Utility functions"""
import os
import sys
import time

from dotenv import load_dotenv
from etherscan import Etherscan  # https://github.com/pcko1/etherscan-python
from sgqlc.endpoint.http import HTTPEndpoint

import queries


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


def get_subgraph_block(etherscan_api_key: str, endpoint: HTTPEndpoint) -> int:
    """Get block number for latest subgraph synced block,
    compare with Etherscan live block (if API key provided)"""
    try:
        block = int(
            endpoint(queries.all_queries["lastSyncedBlock"])["data"]["_meta"]["block"][
                "number"
            ]
        )
        print(f"Subgraph block: {block}")
    except TypeError:
        msg = endpoint(queries.all_queries["lastSyncedBlock"])
        print(msg["errors"][0]["message"])
        sys.exit()

    if etherscan_api_key:
        try:
            eth = Etherscan(etherscan_api_key)
            etherscan_block = int(
                eth.get_block_number_by_timestamp(
                    timestamp=round(time.time()), closest="before"
                )
            )
            print(f"Etherscan block: {etherscan_block}")
            print(
                f"Importing data based on subgraph block: {block}, which is {etherscan_block - block} blocks behind live block."
            )

            if etherscan_block - block >= 100:
                print(
                    f"Warning: Live (Etherscan) block is {etherscan_block - block} blocks ahead of subgraph block. Data may be incomplete."
                )

        except Exception:
            print(
                "Used Etherscan API key, but it's invalid or not working. Continuing."
            )
            print(f"Importing data based on subgraph block: {block}")

        return block
