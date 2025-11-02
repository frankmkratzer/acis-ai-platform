"""
Dagster Repository for ACIS Trading Platform
Defines all assets, jobs, and schedules
"""

from dagster import (
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_modules,
)

from orchestration.assets import market_data, portfolios, technical_indicators

# Load all assets
market_data_assets = load_assets_from_modules([market_data])
technical_indicator_assets = load_assets_from_modules([technical_indicators])
portfolio_assets = load_assets_from_modules([portfolios])

all_assets = [
    *market_data_assets,
    *technical_indicator_assets,
    *portfolio_assets,
]

# Job: Daily market data update (runs after market close)
daily_market_data_job = define_asset_job(
    name="daily_market_data",
    description="Fetch daily price data, news, dividends, and calculate technical indicators",
    selection=AssetSelection.groups("market_data", "technical_indicators"),
)

# Job: Weekly fundamentals update
weekly_fundamentals_job = define_asset_job(
    name="weekly_fundamentals",
    description="Update quarterly/annual financial statements",
    selection=AssetSelection.assets("fundamentals"),
)

# Job: Quarterly portfolio rebalance
quarterly_portfolio_rebalance_job = define_asset_job(
    name="quarterly_portfolio_rebalance",
    description="Rebuild all 8 portfolios (Growth & Value strategies)",
    selection=AssetSelection.groups("portfolios"),
)

# Job: Annual portfolio rebalance (dividend portfolios)
annual_dividend_rebalance_job = define_asset_job(
    name="annual_dividend_rebalance",
    description="Rebuild dividend portfolios (annual rebalance)",
    selection=AssetSelection.assets("portfolios_snapshot"),
)

# Schedule: Daily at 6:00 PM PT (9:00 PM ET - 5hr after market close for data availability)
daily_market_data_schedule = ScheduleDefinition(
    job=daily_market_data_job,
    cron_schedule="0 18 * * 1-5",  # Mon-Fri at 6:00pm PT
    execution_timezone="America/Los_Angeles",
)

# Schedule: Weekly on Sunday at 10am PT
weekly_fundamentals_schedule = ScheduleDefinition(
    job=weekly_fundamentals_job,
    cron_schedule="0 10 * * 0",  # Sunday at 10am PT
    execution_timezone="America/Los_Angeles",
)

# Schedule: Quarterly (first Monday of Jan, Apr, Jul, Oct at 6pm PT)
quarterly_rebalance_schedule = ScheduleDefinition(
    job=quarterly_portfolio_rebalance_job,
    cron_schedule="0 18 1-7 1,4,7,10 1",  # First Monday of quarter at 6pm PT
    execution_timezone="America/Los_Angeles",
)

# Schedule: Annually (first Monday of January at 6pm PT)
annual_rebalance_schedule = ScheduleDefinition(
    job=annual_dividend_rebalance_job,
    cron_schedule="0 18 1-7 1 1",  # First Monday of January at 6pm PT
    execution_timezone="America/Los_Angeles",
)

# Define all resources
defs = Definitions(
    assets=all_assets,
    jobs=[
        daily_market_data_job,
        weekly_fundamentals_job,
        quarterly_portfolio_rebalance_job,
        annual_dividend_rebalance_job,
    ],
    schedules=[
        daily_market_data_schedule,
        weekly_fundamentals_schedule,
        quarterly_rebalance_schedule,
        annual_rebalance_schedule,
    ],
)
