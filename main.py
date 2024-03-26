""" Main script to query, format, and export data from Tinlake
to CSV / Google Sheets Sheets """

import os
import sys
import time
from datetime import datetime

import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe
from sgqlc.endpoint.http import HTTPEndpoint

import format_data
import queries
import utils
import argparse

# Adding this comment to restart github action

def main():
    """Main function to get data, format it, and export it to CSV/Sheets"""
    # Settings
    parser = argparse.ArgumentParser(
        description="Download human-readable data from Centrifuge Tinlake"
    )
    parser.add_argument(
        "--csv", "-c", dest="EXPORT_CSV", default=True, help="Export data as CSV?"
    )
    parser.add_argument(
        "--gsheets",
        "-g",
        dest="EXPORT_GSHEETS",
        default=True,
        help="Export data to gsheets. Note that this requires you to set up credentials, plz see .env.example for more info",
    )
    parser.add_argument(
        "--block",
        "-b",
        dest="CUSTOM_BLOCK",
        default=None,
        type=int,
        help="Specify which block to read data from",
    )
    parser.add_argument("--check-results", "-r", dest="CHECK_RESULTS", default=True)
    parser.add_argument(
        "--graphurl",
        default="https://api.goldsky.com/api/public/project_clhi43ef5g4rw49zwftsvd2ks/subgraphs/main/prod/gn",
        dest="GRAPH_URL",
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Skips tokenbalances query, which is slow, so helps with testing",
    )
    args = parser.parse_args()

    SKIP_LIMIT = 10000000  # How much pagination before we stop

    start = time.time()

    # Cloudflare doesn't like this script unless we spoof a user agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
    }
    endpoint = HTTPEndpoint(args.GRAPH_URL, headers)

    etherscan_api_key, gsheet_credentials, gsheet_file = utils.load_env_vars()

    if args.CUSTOM_BLOCK != None:
        print(f"Using custom block: {args.CUSTOM_BLOCK}")
        block = args.CUSTOM_BLOCK
    else:
        block = utils.get_subgraph_block(etherscan_api_key, endpoint)

    # Time to query!
    all_results = {}

    for key, value in queries.all_queries.items():
        query_name = key
        query = value

        # Skip lastSyncedBlock query from this list
        if query_name == "lastSyncedBlock":
            continue

        # Skip tokenBalances query if we're testing
        if args.test == True and query_name == "tokenBalances":
            continue

        result = pd.DataFrame()

        # Choose how to paginate
        if query_name == "tokenBalances":
            # tokenBalances has one single entry that causes a graphql error
            # So we paginate differently
            # TODO: better algo for this (query 1000, 100, 10, 1 at a time?)
            first = 1
            skip = 0
        else:
            first = 1000
            skip = 0

        while True:
            time.sleep(0.5)  # Sleep to avoid hitting rate limit on graphql endpoint
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

            except Exception:
                # Catches poisoned entries in tokenBalances and skips
                if query_name == "tokenBalances":
                    print("tokenBalances bad data — skipping!")
                else:
                    print(f"Query Error: {result_raw}")
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
        if args.CHECK_RESULTS:
            # Test if pagination needed
            if (len(result_value) % 1000) == 0 and len(result_value) > 0:
                print(
                    f"Warning: {result} may need pagination improvements. Returns exactly {len(result_value)} rows."
                )

            # Test for blank dataframes
            if result_value.empty:
                print(f"Warning: {result} is empty. Import error?")

        # Save as CSV
        if args.EXPORT_CSV:
            if not os.path.exists("results"):
                os.mkdir("results")
            result_value.to_csv(f"results/{result}.csv")

        # Export to google sheets
        if args.EXPORT_GSHEETS:
            # Access google sheet
            gsheet_service_account = gspread.service_account_from_dict(
                gsheet_credentials
            )
            gsheet_sheet = gsheet_service_account.open_by_key(gsheet_file)

            try:
                gsheet_sheet.worksheet(result).clear()
            except gspread.exceptions.WorksheetNotFound:
                print(f"No existing worksheet found for {result}. Creating new one.")
                (
                    rows,
                    columns,
                ) = result_value.shape  # get num of rows and columns from dataframe
                gsheet_sheet.add_worksheet(title=result, rows=rows, cols=columns)

            set_with_dataframe(gsheet_sheet.worksheet(result), result_value)
            print(f"Imported {result} to Google Sheets")
            time.sleep(0.5)  # Sleep to avoid hitting rate limit

    # Export time last updated to google sheets
    if args.EXPORT_GSHEETS:
        gsheet_sheet.worksheet("Status / Config").update_acell(
            "B1", str(datetime.now())
        )
        print(f"Updated status sheet in Google Sheets")

    end = time.time()
    elapsed = end - start

    if elapsed > 120:
        print(f"Complete. Time elapsed: {round((elapsed) / 60, 1)} minutes.")
    else:
        print(f"Complete. Time elapsed: {round(elapsed, 1)} seconds.")

    sys.exit(0)


if __name__ == "__main__":
    main()
