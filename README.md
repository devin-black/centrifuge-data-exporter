# centrifuge-data-exporter
This repository contains a Python script that can be used to download complete, human-readable data on Centrifuge's Ethereum-based Tinlake platform.

<details>
<summary>Data that this program queries from Tinlake:</summary>
    <ul>
        <li>Pools
        <li>Pools
        <li>Daily pool data
        <li>Loans
        <li>ERC20 transfers
        <li>Tokens
        <li>Investor token balances
        <li>Daily investor token balances
        <li>Daily CFG rewards
        <li>Issuer CFG rewards
        <li>Ethereum / Centrifuge Chain links
        <li>Pool investors
    <ul>
</details>

## Prerequisites
You will need the following tools to run this script:

- Python 3
- pip (Python package manager)

## Running the program
1. Clone this repository to your local machine:

    `git clone https://github.com/devin-black/centrifuge-data-exporter.git`

2. Navigate to the cloned directory and create a virtual environment. This will create a new virtual environment called venv.

    `cd centrifuge-data-exporter`

    `python -m venv venv`

4. Activate the virtual environment:
    
    `source venv/bin/activate`

5. Finally, install the required dependencies using pip:

    `pip install -r requirements.txt`


6. Run the script

    `python3 main.py`
    `python3 main.py -b 16593567 -t`

Run with the "--help" argument to see all args

## Settings

You can define a few custom settings. This is optional. Without env vars or a .env file, the program will default to only exporting CSVs.

Create a copy of .env.example and rename it to .env. Then, fill in the values:

- If you want to export to Google sheets, you will need to put into the env vars the sheet file path as well as your authentication credentials from the auth.json file Google provides. [Follow these directions to set up Google Sheets](https://docs.gspread.org/en/v5.7.0/oauth2.html).
- Specify an [Etherscan API key](https://etherscan.io/myapikey), so the program can tell you if the subgraph is synced up with the last block on Ethereum and warn you if it's >100 blocks behind.

If no env vars or .env file is provided, the program will use default endpoints and export only CSV files.
It will also not ping Etherscan to get the current block to compare with the subgraph's current block
(This is not necessary, but can be useful to know if the subgraph is synced up with the last block on Ethereum.)

## Command Line Arguments

This program accepts the following command line arguments:

1. `--csv` or `-c`: (Optional) Export data as CSV? Set to `True` by default. To disable CSV export, use `--csv False`.

2. `--gsheets` or `-g`: (Optional) Export data to gsheets. Set to `True` by default. Note that this requires you to set up credentials, please see `.env.example` for more information. To disable gsheets export, use `--gsheets False`.

3. `--block` or `-b`: (Optional) Specify which block to read data from. Provide an integer value. Default is `None`, which will read data from the latest block.

4. `--check-results` or `-r`: (Optional) Enable or disable result checking. Set to `True` by default. To disable result checking, use `--check-results False`.

5. `--graphurl`: (Optional) Provide a custom URL for the Tinlake Graph API. Default is `https://graph.centrifuge.io/tinlake`.

6. `--test` or `-t`: (Optional) Skips the tokenbalances query, which is slow, to help with testing. Use this flag without a value.


## Current issues / todo
- **These queries max out at 5k results** due to Subgraph limits, even with pagination. Fix will either be expand Subgraph 5k limit or query by pool.
    - `dailyPoolDatas`,
    - `erc20Transfers`
    - `dailyInvestorTokenBalances`, 
- Implement some of these as-of-yet unimplemented queries:
    - `rewardbyToken`
    - `account`
    - `poolsbyAORewardRecipient`
    - `Day`
    - `Proxy`
    - `PoolRegistry`
    - `GlobalAccountID`
- Better `tokenBalances` algo
- Implement Subquery to do the same for pools on Centrifuge Chain!