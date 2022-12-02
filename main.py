import time
import os
import json

import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe
from sgqlc.endpoint.http import HTTPEndpoint
import traceback
from dotenv import load_dotenv
from etherscan import Etherscan #https://github.com/pcko1/etherscan-python

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
        use_custom_block = json.loads(os.getenv('USE_CUSTOM_BLOCK').lower())
        if use_custom_block:
            custom_block = int(os.getenv('CUSTOM_BLOCK'))
    except Exception as e:
        print(f"No valid .env file — using default settings. (Error: {e}")
        graph_url = "https://api.thegraph.com/subgraphs/name/centrifuge/tinlake"
        etherscan_api_key = False
        gsheets_auth_path = None
        gsheets_file = None
        export_csv = True
        export_gsheets = False
        test = True
        use_custom_block = False

    endpoint = HTTPEndpoint(url=graph_url)
    skip_limit = 5000 #Subgraph limits skip to 5000. TODO - can we get around this?

    #Get block number for latest subgraph synced block, compare with Etherscan live block (if API key provided)
    block = int(endpoint(queries.last_synced_block_query)['data']['_meta']['block']['number'])
    print(f"Subgraph block:  {block}")

    if etherscan_api_key:
        try:
            eth = Etherscan(etherscan_api_key)
            etherscan_block = int(eth.get_block_number_by_timestamp(timestamp=round(time.time()), closest="before"))
            print(f"Etherscan block: {etherscan_block}")
            print(f"Importing data based on subgraph block: {block}, which is {etherscan_block - block} blocks behind live block.")
            
            if etherscan_block - block >= 100:
                print(f"Warning: Live (Etherscan) block is {etherscan_block - block} blocks ahead of subgraph block. Data may be incomplete.")

        except Exception as e:
                print(f"Warning: used Etherscan API key, but it's invalid or not working: {e}")
                print(f"Importing data based on subgraph block: {block}")
    
    #Time to query!
    all_results = {}
    iferrors = False
    retries = 0
  
    for i in queries.all_queries:
        query = queries.all_queries[i]
        result = pd.DataFrame()

        #Choose how to paginate
        if i == 'tokenBalances': 
            #tokenBalances has one single entry that causes a graphql error, so paginate differently
            #TODO: better algo for this (query 1000, 100, 10, 1 at a time?)
            first = 1
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

                if use_custom_block:
                    result_raw = endpoint(query, {'block': custom_block, 'first': first, 'skip': skip})
                else:
                    result_raw = endpoint(query, {'block': block, 'first': first, 'skip': skip})

                if i == 'loans': #Workaround for loans query — faster to pull via pools
                    #result_temp = pd.DataFrame(result_raw['data'])
                    result_temp = pd.DataFrame(result_raw['data']['pools'][0]['loans'])
                else:
                    result_temp = pd.DataFrame(result_raw['data'][i])
            
            except Exception as e:
                if i == 'tokenBalances': #Catches poisoned entries in tokenBalances
                    print(f"tokenBalances bad data — skipping!")
                else:
                    print(f"Error: {e}") 
                    iferrors = True

            if result_temp.empty or skip >= skip_limit: #Done fetching results
                print("                                              ", end="\r")
                print(f"Querying:   {i} — Done.", end="\r")
                break 
            else: #Add fetched paginated data to full result and increment skip
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

            #Temp fix to not break existing formulas
            #Append two empty columns to left side of dataframe X
            if result != 'poolInvestors':
                all_results[result] = pd.concat([pd.DataFrame(columns=['','']), all_results[result]], axis=1, join='outer')
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