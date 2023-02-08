import os
import sys
import time

import gspread
import pandas as pd
from etherscan import Etherscan  # https://github.com/pcko1/etherscan-python
from gspread_dataframe import set_with_dataframe
from sgqlc.endpoint.http import HTTPEndpoint

import format_data
import queries
import utils


def get_subgraph_block(etherscan_api_key: str, endpoint: HTTPEndpoint) -> int:
    # Get block number for latest subgraph synced block, compare with Etherscan live block (if API key provided)
    # Also tests if subgraph url is working
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


def main():
    """Main function to get data, format it, and export it to CSV / Sheets"""
    # Settings
    EXPORT_CSV = True
    EXPORT_GSHEETS = True
    USE_CUSTOM_BLOCK = False  # TODO - make command line vars?
    CUSTOM_BLOCK = 0
    TEST = True
    GRAPH_URL = "https://graph.centrifuge.io/tinlake"
    SKIP_LIMIT = 5000  # Subgraph limits skip to 5000. TODO - can we get around this?

    start = time.time()

    endpoint = HTTPEndpoint(url=GRAPH_URL)

    etherscan_api_key, gsheet_credentials, gsheet_file = utils.load_env_vars()

    if USE_CUSTOM_BLOCK:
        print(f"Using custom block: {CUSTOM_BLOCK}")
        block = CUSTOM_BLOCK
    else:
        block = get_subgraph_block(etherscan_api_key, endpoint)

    # Time to query!
    all_results = {}

    for key, value in queries.all_queries.items():
        query_name = key
        query = value
        result = pd.DataFrame()

        # Choose how to paginate
        if query_name == "tokenBalances":
            # tokenBalances has one single entry that causes a graphql error, so paginate differently
            # TODO: better algo for this (query 1000, 100, 10, 1 at a time?)
            first = 1
            skip = 0
        else:
            first = 1000
            skip = 0

        while True:
            try:
                if first == 1:
                    print(f"Querying:   {query_name} #{skip}…", end="\r")
                else:
                    print(f"Querying:   {query_name} #{skip}–{skip + first}…", end="\r")

                result_raw = endpoint(
                    query, {"block": block, "first": first, "skip": skip}
                )

                # Workaround for loans query — faster to pull via pools
                if query_name == "loans":
                    result_temp = pd.DataFrame(result_raw["data"]["pools"][0]["loans"])
                else:
                    result_temp = pd.DataFrame(result_raw["data"][query_name])

            except Exception as exception:
                # Catches poisoned entries in tokenBalances and skips
                if query_name == "tokenBalances":
                    print("tokenBalances bad data — skipping!")
                else:
                    print(f"Query Error: {exception}")
                    sys.exit()

            # Add fetched paginated data to full result and increment skip
            result = pd.concat([result, result_temp], axis=0, join="outer")
            if skip < SKIP_LIMIT:
                skip += first

            # See if we are done fetching results
            if result_temp.empty or skip >= SKIP_LIMIT:
                print("                                              ", end="\r")
                print(f"Querying:   {query_name} — Done.", end="\r")
                break

        # Format results and add to all_results dict
        result = format_data.formatter(result, query_name)
        print(f"\rQuerying:   {query_name} — Done. Formatting successful.")

        all_results[query_name] = result

    for result, result_value in all_results.items():
        # Test data for potential issues
        if TEST:
            # Test if pagination needed
            if (len(result_value) % 1000) == 0 and len(result_value) > 0:
                print(
                    f"Warning: {result} may need pagination improvements. Returns exactly {len(result_value)} rows."
                )

            # Test for blank dataframes
            if result_value.empty:
                print(f"Warning: {result} is empty. Import error?")

        # Save as CSV
        if EXPORT_CSV:
            if not os.path.exists("results"):
                os.mkdir("results")
            result_value.to_csv(f"results/{result}.csv")

        # Export to google sheets
        if EXPORT_GSHEETS:
            # Access google sheet
            gc = gspread.service_account_from_dict(gsheet_credentials)
            sh = gc.open_by_key(gsheet_file)

            try:
                sh.worksheet(result).clear()
            except gspread.exceptions.WorksheetNotFound:
                print(f"No existing worksheet found for {result}. Creating new one.")
                r, c = result_value.shape  # get num of rows and columns from dataframe
                sh.add_worksheet(title=result, rows=r, cols=c)

            set_with_dataframe(sh.worksheet(result), result_value)
            print(f"Imported {result} to Google Sheets")
            time.sleep(0.5)  # Sleep to avoid hitting rate limit

    end = time.time()
    elapsed = end - start

    if elapsed > 120:
        print(f"Complete. Time elapsed: {round((elapsed) / 60, 1)} minutes.")
    else:
        print(f"Complete. Time elapsed: {round(elapsed, 1)} seconds.")

    sys.exit(0)


if __name__ == "__main__":
    main()
