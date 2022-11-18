#TODO
#Check if missing any newish possible queries
#Format day timestamps to date in format.py
#Figure out what to do with queries with more than 5k results (5k current maximum pagination
#fix 524 error handling?

import time
import os
import json

import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe
from sgqlc.endpoint.http import HTTPEndpoint
from dotenv import load_dotenv
import traceback
from etherscan import Etherscan  # https://github.com/pcko1/etherscan-python

import queries
import format

def main():
    start = time.time()

    #Load environment settings
    try:
        load_dotenv()
        graph_url = os.getenv('SUBGRAPH_URL')
        etherscan_api_key = os.getenv('ETHERSCAN_API_KEY')
        gsheets_auth_path = os.getenv('GSHEETS_AUTH_PATH')
        gsheets_file = os.getenv('GSHEETS_FILE')
        
        #Unfortunately hacky way of converting ENV file bools (strings) to proper bools
        export_csv = json.loads(os.getenv('EXPORT_CSV').lower())
        export_gsheets = json.loads(os.getenv('EXPORT_GSHEETS').lower())
        test = json.loads(os.getenv('TEST').lower())
    except:
        print('Error loading environment variables. Is your .env file set up properly?')

    #Hardcoded settings
    skip_limit = 5000 #Subgraph limits skip to 5000. TODO - how to get around this?
    endpoint = HTTPEndpoint(url=graph_url)

    #Get block number for latest subgraph synced block, compare with Etherscan live block (if API key provided)
    block = int(endpoint(queries.last_synced_block_query)['data']['_meta']['block']['number'])

    if etherscan_api_key:
        current_time = round(time.time())
        eth = Etherscan(etherscan_api_key)
        etherscan_block = int(eth.get_block_number_by_timestamp(timestamp=current_time, closest="before"))

        if etherscan_block - block >= 100:
            print(f"Warning: Live (Etherscan) block is {etherscan_block - block} blocks ahead of subgraph block. Data may be incomplete.")

        print(f"Subgraph block:  {block}")
        print(f"Etherscan block: {etherscan_block}")
        print(f"Importing data based on subgraph block: {block}, which is {etherscan_block - block} blocks behind live block.")
 
    else:
        print("No valid Etherscan API key provided. Skipping Etherscan block check.")
        print(f"Importing data based on subgraph block: {block}")

    #Loop through dict in queries.py of all queries. Query and format.
    all_results = {}
    iferrors = False
    retries = 0
  
    for i in queries.all_queries:
        query = queries.all_queries[i]
        result = pd.DataFrame()

        if i == 'tokenBalances': 
            #tokenBalances has one single entry that causes a graphql error, so paginate differently
            #TODO: better algo for this (query 1000, 100, 10, 1 at a time?)
            first = 1
            skip = 0
        elif i == 'loans': 
            #loans times out on larger queries sometimes, so take it slower
            first = 100
            skip = 0
        else:
            first = 1000
            skip = 0

        while True:
            try:
                if first == 1:
                    print(f"Querying:   {i} #{skip}…", end="\r")
                else:
                    print(f"Querying:   {i} #{skip}–{skip + first}…", end="\r")

                result_raw = endpoint(query, {'block': block, 'first': first, 'skip': skip})
                result_temp = pd.DataFrame(result_raw['data'][i])
            except:
                if i == 'tokenBalances': #Catches poisoned entries in tokenBalances
                    print(f"tokenBalances bad data — skipping!")
                else: #Other error
                    try: #Try to get tidy error message if Graphql gives it
                        error_msg = result_raw['errors'][0]['message']
                        print(f"Graphql error: {error_msg}")
                        if error_msg == 'HTTP Error 524' and retries < 3: #need to correct error msg probs
                            print(f"Retrying in 10 seconds… (Try #{retries}") 
                            time.sleep(10)
                            retries += 1
                            continue
                        elif error_msg == 'HTTP Error 524' and retries > 3:
                            print(f"Still timing out. Aborting {i}.")
                            iferrors = True
                            break
                    except: #no pretty errors? too bad
                        print(f"Other error: {result_raw}")
                        traceback.print_exc()
                        iferrors = True
                        break

            if result_temp.empty or skip >= skip_limit: #Done fetching results
                print("                                              ", end="\r")
                print(f"Querying:   {i} — Done.", end="\r")
                break 
            else: #Add fetched paginated data to full result
                result = pd.concat([result, result_temp], axis=0, join='outer')
                if skip < skip_limit:
                    skip += first

        #Format
        try:
            result = format.formatter(result, i)
            print(f"\rQuerying:   {i} — Done. Formatting successful.")
        except Exception as e:
            traceback.print_exc()
            print("Error: Formatting failed.")
            iferrors = True

        all_results[i] = result

    #Test data for potential issues
    if test:
        #Test if pagination needed
        for result in all_results:
            if (len(all_results[result]) % 1000) == 0 and len(all_results[result]) > 0:
                print(f"Warning: {result} may need pagination improvements. Returns exactly {len(all_results[result])} rows.")

        #Test for blank dataframes
        for result in all_results:
            if all_results[result].empty:
                print(f"Warning: {result} is empty. Import error?")

    #Save as CSV
    if export_csv:
        for result in all_results:
            all_results[result].to_csv(f'/Users/devinblack/documents/github/tinlake-data-v3/results/{result}.csv')
        
        print("CSV export complete.")

    #Export to google sheets
    if export_gsheets:
        #Access google sheet
        gc = gspread.service_account(filename = gsheets_auth_path)
        sh = gc.open_by_key(gsheets_file)

        for result in all_results:
            try:
                sh.worksheet(result).clear()
            except:
                print(f"No existing worksheet found for {result}. Creating new one.")
                r, c = all_results[result].shape #get num of rows and columns from dataframe
                sh.add_worksheet(title = result, rows = r, cols = c)

            set_with_dataframe(sh.worksheet(result), all_results[result])
            print(f"Imported {result} to Google Sheets")

        print("Google Sheets export complete.")

    end = time.time()
    elapsed = end - start

    if elapsed > 120:
        print(f"Complete. Time elapsed: {round((elapsed) / 60, 1)} minutes.")
    else:
        print(f"Complete. Time elapsed: {round(elapsed, 1)} seconds.")

    if iferrors:
        print("There were errors. Check logs. Data may be incomplete.")
    
    exit(0)

if __name__ == "__main__":
    main()