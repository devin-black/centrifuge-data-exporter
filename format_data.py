"""Functions to format data from subgraph queries
Makes the data more human readable for easy reading in spreadsheets"""

import pandas as pd
from dotenv import load_dotenv

# Functions that will format subgraph data (once in dataframe form)
# Makes data more human readable.


def format_decimal(df, columns, places):
    """Restore decimal places to columns in dataframe. Usually to 18 or 27 places for Tinlake.
    Could automate this, but I like the specific control here.
    Takes list of dataframe column names."""
    for column in columns:
        df[column] = df[column].astype(float)
        df[column] = df[column].apply(lambda x: x / 10**places)
    return df


def format_timestamp(df, column):
    """Converts timestamp to human readable date"""
    df[column] = pd.to_datetime(df[column], unit="s")
    return df


# Per-query data formatting logic
def formatter(df, query):
    if query == "pools":
        columns_18 = [
            "totalDebt",
            "totalBorrowsAggregatedAmount",
            "totalRepaysAggregatedAmount",
            "seniorDebt",
            "maxReserve",
            "reserve",
            "assetValue",
        ]
        columns_27 = [
            "weightedInterestRate",
            "seniorInterestRate",
            "minJuniorRatio",
            "maxJuniorRatio",
            "currentJuniorRatio",
            "seniorTokenPrice",
            "juniorTokenPrice",
            "juniorYield30Days",
            "seniorYield30Days",
            "juniorYield90Days",
            "seniorYield90Days",
        ]
        format_decimal(df, columns_18, 18)
        format_decimal(df, columns_27, 27)
        return df

    if query == "dailyPoolDatas":
        columns_18 = [
            "reserve",
            "totalDebt",
            "assetValue",
            "seniorDebt",
            "currentJuniorRatio",
        ]
        columns_27 = [
            "seniorTokenPrice",
            "juniorTokenPrice",
            "juniorYield30Days",
            "seniorYield30Days",
            "juniorYield90Days",
            "seniorYield90Days",
        ]
        format_decimal(df, columns_18, 18)
        format_decimal(df, columns_27, 27)
        format_timestamp(df, "day")
        df["day"] = [d.get("id") for d in df.day]
        df["pool"] = [d.get("id") for d in df.pool]
        return df

    if query == "loans":
        columns_18 = [
            "borrowsAggregatedAmount",
            "ceiling",
            "debt",
            "repaysAggregatedAmount",
            "threshold",
        ]
        columns_27 = ["interestRatePerSecond"]
        format_decimal(df, columns_18, 18)
        format_decimal(df, columns_27, 27)
        format_timestamp(df, "opened")
        format_timestamp(df, "closed")
        format_timestamp(df, "maturityDate")
        format_timestamp(df, "financingDate")
        df["pool"] = [d.get("id") for d in df.pool]
        return df

    if query == "erc20Transfers":
        format_decimal(df, ["amount"], 18)
        df["token"] = [d.get("id") for d in df.token]
        df["pool"] = [d.get("id") for d in df.pool]
        return df

    if query == "tokens":
        format_decimal(df, ["price"], 27)
        return df

    if query == "tokenBalances":
        columns_18 = [
            "balanceAmount",
            "balanceValue",
            "totalAmount",
            "totalValue",
            "pendingSupplyCurrency",
            "supplyAmount",
            "supplyValue",
            "pendingRedeemToken",
            "redeemAmount",
        ]
        format_decimal(df, columns_18, 18)
        df["owner"] = [d.get("id") for d in df.owner]
        df["token"] = [d.get("id") for d in df.token]
        return df

    if query == "dailyInvestorTokenBalances":
        columns_18 = [
            "seniorTokenAmount",
            "seniorTokenValue",
            "seniorSupplyAmount",
            "seniorPendingSupplyCurrency",
            "juniorTokenAmount",
            "juniorTokenValue",
            "juniorSupplyAmount",
            "juniorPendingSupplyCurrency",
        ]
        format_decimal(df, columns_18, 18)
        format_timestamp(df, "day")
        df["account"] = [d.get("id") for d in df.account]
        df["day"] = [d.get("id") for d in df.day]
        df["pool"] = [d.get("id") for d in df.pool]
        return df

    if query == "rewardDayTotals":
        columns_18 = [
            "toDateAORewardAggregateValue",
            "toDateRewardAggregateValue",
            "toDateAggregateValue",
            "todayAOReward",
            "todayReward",
            "todayValue",
        ]
        format_decimal(df, columns_18, 18)
        format_timestamp(df, "id")
        return df

    if query == "rewardBalances":
        columns_18 = ["linkableRewards", "totalRewards"]
        format_decimal(df, columns_18, 18)
        format_timestamp(df, "timestamp")
        return df

    if query == "aorewardBalances":
        columns_18 = ["linkableRewards", "totalRewards"]
        format_decimal(df, columns_18, 18)
        return df

    if query == "rewardLinks":
        format_decimal(df, ["rewardsAccumulated"], 18)
        return df

    # poolInvestors query is done differently. Returns a list of addresses per pool ID
    # To make spreadsheet-friendly: we pivot so row 1 in a column is pool ID, subsequent rows are addresses in that pool
    if query == "poolInvestors":
        columns_list = []
        for index, row in df.iterrows():
            column = [
                row["id"]
            ]  # Extract pool ID of this row and make it first entry in column list
            addresses = row[1]  # Extract addresses of this row
            column = column + addresses  # Add addresses under column in list
            columns_list.append(column)  # Add this to list of columns

        df = pd.DataFrame(columns_list)  # Turn list of columns into a dataframe
        df = df.T  # Pivot.
        return df

    else:
        print(f"Formatting for query not found (or not needed?) for {query}")
        return df
