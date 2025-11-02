# Portfolio Management System

Rule-based portfolio screener implementing the 8-portfolio strategy from CLAUDE.md

## Overview

This system constructs 8 portfolios across 3 strategies (Dividend, Growth, Value) and 3 market caps (Large, Mid, Small):

**Dividend Portfolios (2):**
- Dividend - Large Cap
- Dividend - Mid Cap

**Growth Portfolios (3):**
- Growth - Large Cap
- Growth - Mid Cap
- Growth - Small Cap

**Value Portfolios (3):**
- Value - Large Cap
- Value - Mid Cap
- Value - Small Cap

## Files

- `config.py` - All strategy criteria from CLAUDE.md
- `screener.py` - Stock screening engine
- `portfolio_builder.py` - Portfolio construction system

## Usage

### Build All 8 Portfolios

```bash
cd portfolio
python portfolio_builder.py
```

This will:
1. Screen the universe for each strategy/market cap combination
2. Apply universal filters (price >$5, volume, fundamentals)
3. Apply strategy-specific filters (dividend/growth/value criteria)
4. Rank candidates and select top 15 per portfolio
5. Save results to **database** (primary)
6. Also save backup to `portfolios_YYYY-MM-DD.json`

### Query Portfolios from Database

```sql
-- View all portfolios
SELECT * FROM portfolios;

-- View latest snapshot for each portfolio
SELECT
    p.name,
    ps.snapshot_date,
    ps.position_count,
    ps.candidates_screened
FROM portfolios p
JOIN portfolio_snapshots ps ON p.portfolio_id = ps.portfolio_id
WHERE ps.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM portfolio_snapshots
    WHERE portfolio_id = p.portfolio_id
)
ORDER BY p.name;

-- View holdings for a specific portfolio
SELECT
    ph.rank,
    ph.ticker,
    ph.weight,
    ph.score
FROM portfolio_holdings ph
JOIN portfolio_snapshots ps ON ph.snapshot_id = ps.snapshot_id
WHERE ps.portfolio_id = 'growth_large'
  AND ps.snapshot_date = '2025-10-26'
ORDER BY ph.rank;
```

### Test Individual Screener

```bash
python screener.py
```

## Strategy Criteria

### Universal Filters (All Portfolios)
- Stock type: US Common Stock
- Price: > $5
- Volume: > 100K avg daily
- ROE: >= 15%
- Debt-to-Equity: <= 2.0
- Positive operating cash flow

### Dividend Strategy
- Eligible: Large Cap, Mid Cap only
- Yield: 3-12%
- Payout ratio: <= 75%
- Dividend history: 10+ years
- Rebalance: Annual

### Growth Strategy
- Eligible: All market caps
- Revenue growth: >= 20% (3-year)
- Earnings growth: >= 25% (3-year)
- PEG ratio: < 2.0
- EMA 12 > EMA 26
- Price > SMA 50
- RSI: 30-70
- Sentiment: >= 0.3
- Rebalance: Quarterly

### Value Strategy
- Eligible: All market caps
- P/E: < 15
- P/B: < 3.0
- P/S: < 2.0
- FCF yield: >= 5%
- EMA 12 > EMA 26
- Price > SMA 50
- RSI: 20-50
- Sentiment: >= 0.2
- Rebalance: Quarterly

## Next Steps

**Phase 1 Complete** - Rule-based screener working

**Phase 2: ML Enhancement**
1. Feature engineering pipeline
2. XGBoost ranking models (replace simple scoring)
3. LSTM price forecasting
4. Sentiment analysis (FinBERT)

**Phase 3: Production System**
1. Rebalancing automation
2. Performance tracking
3. Risk management monitoring
4. Schwab integration

## Testing

Once data backfills complete, test with:

```bash
# Test with current data
python portfolio_builder.py

# Expected output:
# - 8 portfolios with up to 15 positions each
# - JSON file with complete portfolio details
# - Summary statistics
```

## Notes

- Currently uses simple momentum-based ranking
- ML models will replace ranking logic in Phase 2
- Some filters may need adjustment based on data availability
- Sentiment scoring uses basic positive/negative/neutral mapping
