# Backfill Scripts

All backfill scripts for populating historical data from Polygon.io API.

## Usage

All log files should be written to the `logs/` directory in the project root.

### Running Individual Backfill Scripts

```bash
# Price data
python scripts/backfill/populate_daily_bars.py 2>&1 | tee logs/daily_bars_backfill.log

# Dividends and splits
python scripts/backfill/populate_dividends.py 2>&1 | tee logs/dividends_backfill.log
python scripts/backfill/populate_splits.py 2>&1 | tee logs/splits_backfill.log

# Fundamental data
python scripts/backfill/populate_balance_sheets.py 2>&1 | tee logs/balance_sheets_backfill.log
python scripts/backfill/populate_cash_flow_statements.py 2>&1 | tee logs/cash_flow_statements_backfill.log
python scripts/backfill/populate_income_statements.py 2>&1 | tee logs/income_statements_backfill.log
python scripts/backfill/populate_ratios.py 2>&1 | tee logs/ratios_backfill.log

# Technical indicators
python scripts/backfill/populate_sma.py 2>&1 | tee logs/sma_backfill.log
python scripts/backfill/populate_ema.py 2>&1 | tee logs/ema_backfill.log
python scripts/backfill/populate_rsi.py 2>&1 | tee logs/rsi_backfill.log
python scripts/backfill/populate_macd.py 2>&1 | tee logs/macd_backfill.log

# Market data
python scripts/backfill/populate_short_interest.py 2>&1 | tee logs/short_interest_backfill.log
python scripts/backfill/populate_ipos.py 2>&1 | tee logs/ipos_backfill.log
python scripts/backfill/populate_ticker_events.py 2>&1 | tee logs/ticker_events_backfill.log

# News and sentiment
python scripts/backfill/populate_news.py 2>&1 | tee logs/news_backfill.log

# Company overview
python scripts/backfill/populate_ticker_overview.py 2>&1 | tee logs/ticker_overview_backfill.log
```

### Table Creation Scripts

Before running population scripts, ensure tables are created:

```bash
python scripts/backfill/create_<table_name>_table.py
```

Available table creation scripts:
- `create_dividends_table.py`
- `create_splits_table.py`
- `create_balance_sheets_table.py`
- `create_cash_flow_statements_table.py`
- `create_income_statements_table.py`
- `create_ratios_table.py`
- `create_short_interest_table.py`
- `create_sma_table.py`
- `create_ema_table.py`
- `create_rsi_table.py`
- `create_ipos_table.py`
- `create_ticker_events_table.py`
- `create_news_table.py`
- `create_macd_table.py`
- `create_portfolio_tables.py`

## Notes

- All logs are written to `logs/` directory (ignored by git)
- Use `2>&1 | tee logs/<filename>.log` to see output in terminal AND save to file
- Background processes should redirect to logs directory
- Check progress: `tail -f logs/<filename>.log`
