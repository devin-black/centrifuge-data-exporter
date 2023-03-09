"""
Dict of queries used to import data from the subgraph.
Tinlake subgraph schema can be found here:
https://github.com/centrifuge/tinlake-subgraph/blob/main/schema.graphql
Can likely automate this, but hardcoded queries avoid unexpected breaks if subgraph updated
"""

all_queries = {
    "lastSyncedBlock": """
{
  _meta {
    block {
      number
    }
  }
}
""",
    "pools": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
  pools(first: $first, skip: $skip, block:{number: $block})
  {
    id
    totalDebt
    totalBorrowsCount
    totalBorrowsAggregatedAmount
    totalRepaysCount
    totalRepaysAggregatedAmount
    weightedInterestRate
    seniorDebt
    seniorInterestRate
    minJuniorRatio
    maxJuniorRatio
    currentJuniorRatio
    maxReserve
    seniorTokenPrice
    juniorTokenPrice
    juniorYield30Days
    seniorYield30Days
    juniorYield90Days
    seniorYield90Days
    assetValue
    reserve
    shortName
    version
  }
}
""",
    "dailyPoolDatas": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
  dailyPoolDatas(first: $first, skip: $skip)
  {
    id
    day {
      id
    }
    pool {
      id
    }
    reserve
    totalDebt
    assetValue
    seniorDebt
    seniorTokenPrice
    juniorTokenPrice
    currentJuniorRatio
    juniorYield30Days
    seniorYield30Days
    juniorYield90Days
    seniorYield90Days
  }
}
""",
    "loans": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
  pools
  {
    loans(first: $first, skip: $skip, block:{number: $block})
    {
      id
      pool {
        id
      }
      index
      nftId
      nftRegistry
      owner
      opened
      closed
      debt
      interestRatePerSecond
      ceiling
      threshold
      borrowsCount
      borrowsAggregatedAmount
      repaysCount
      repaysAggregatedAmount
      maturityDate
      financingDate
      riskGroup
    }
  }
}
""",
    "erc20Transfers": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
    erc20Transfers(first: $first, skip: $skip, block:{number: $block})
    {
        id
        transaction
        token {
          id
        }
        from
        to
        amount
        pool {
          id
        }
    }
}
""",
    "tokens": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
    tokens(first: $first, skip: $skip, block:{number: $block})
    {
        id
        symbol
        price
    }
}
""",
    # TODO probably fix this as some stuff was changed here
    "rewardDayTotals": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
  rewardDayTotals(first: $first, skip: $skip, block:{number: $block})
  {
    id
    aoRewardRate
    dropRewardRate
    tinRewardRate
    toDateAORewardAggregateValue
    toDateAggregateValue
    toDateRewardAggregateValue
    todayAOReward
    todayReward
    todayValue
  }
}
""",
    "aorewardBalances": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
  aorewardBalances(first: $first, skip: $skip, block:{number: $block})
  {
    id
    linkableRewards
    totalRewards
  }
}
""",
    "rewardLinks": """
query ($block: Int!, $first: Int!, $skip: Int!)
{
  rewardLinks(first: $first, skip: $skip, block:{number: $block})
  {
    id
    ethAddress
    centAddress
    rewardsAccumulated
  }
}
""",
    "poolInvestors": """
    query ($block: Int!, $first: Int!, $skip: Int!)
    {
      poolInvestors(first: $first, skip: $skip, block:{number: $block})
      {
        id
        accounts
      }
    }
    """,
    # TODO: Add in logic to paginate through tokenBalance
    # Buggy data causes query of 1000 to fail. Start with 100.
    "tokenBalances": """
  query ($block: Int!, $first: Int!, $skip: Int!)
  {
    tokenBalances(first: $first, skip: $skip, block:{number: $block})
    {
      id
      owner {
        id
      }
      balanceAmount
      balanceValue
      totalAmount
      totalValue
      token {
        id
      }
      pendingSupplyCurrency
      supplyAmount
      supplyValue
      pendingRedeemToken
      redeemAmount
    }
  }
  """,
    "dailyInvestorTokenBalances": """
    query ($block: Int!, $first: Int!, $skip: Int!)  
    {
      dailyInvestorTokenBalances(first: $first, skip: $skip)
      {
        id
        account {
          id
        }
        day {
          id
        }
        pool {
          id
        }
        seniorTokenAmount
        seniorTokenValue
        seniorSupplyAmount
        seniorPendingSupplyCurrency
        juniorTokenAmount
        juniorTokenValue
        juniorSupplyAmount
        juniorPendingSupplyCurrency
      }
    }
    """,
}
