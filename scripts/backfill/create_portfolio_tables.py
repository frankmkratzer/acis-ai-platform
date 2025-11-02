#!/usr/bin/env python3
"""
Create portfolio management tables
Tracks portfolios, holdings, and rebalancing history
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_tables():
    """Create portfolio management tables"""

    create_sql = """
        -- Portfolio definitions (the 8 portfolios)
        CREATE TABLE IF NOT EXISTS portfolios (
            portfolio_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            strategy VARCHAR(20) NOT NULL,  -- dividend, growth, value
            market_cap VARCHAR(20) NOT NULL,  -- large_cap, mid_cap, small_cap
            target_position_count INTEGER DEFAULT 15,
            rebalance_frequency VARCHAR(20) NOT NULL,  -- annual, quarterly
            active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Portfolio snapshots (point-in-time portfolio state)
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            snapshot_id SERIAL PRIMARY KEY,
            portfolio_id VARCHAR(50) NOT NULL REFERENCES portfolios(portfolio_id),
            snapshot_date DATE NOT NULL,
            snapshot_type VARCHAR(20) NOT NULL,  -- rebalance, daily_update, inception
            position_count INTEGER,
            candidates_screened INTEGER,
            total_value NUMERIC(20,2),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (portfolio_id, snapshot_date, snapshot_type)
        );

        -- Portfolio holdings (positions at each snapshot)
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            holding_id SERIAL PRIMARY KEY,
            snapshot_id INTEGER NOT NULL REFERENCES portfolio_snapshots(snapshot_id) ON DELETE CASCADE,
            portfolio_id VARCHAR(50) NOT NULL REFERENCES portfolios(portfolio_id),
            ticker VARCHAR(20) NOT NULL,
            weight NUMERIC(10,6) NOT NULL,  -- Position weight (0.0 to 1.0)
            score NUMERIC(20,6),  -- Ranking score
            rank INTEGER,  -- Rank within portfolio (1 = highest)
            shares INTEGER,  -- Number of shares (if known)
            entry_price NUMERIC(20,4),  -- Entry price
            entry_value NUMERIC(20,2),  -- Position value at entry
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Rebalancing events
        CREATE TABLE IF NOT EXISTS rebalancing_events (
            event_id SERIAL PRIMARY KEY,
            portfolio_id VARCHAR(50) NOT NULL REFERENCES portfolios(portfolio_id),
            rebalance_date DATE NOT NULL,
            prev_snapshot_id INTEGER REFERENCES portfolio_snapshots(snapshot_id),
            new_snapshot_id INTEGER REFERENCES portfolio_snapshots(snapshot_id),
            positions_added INTEGER,
            positions_removed INTEGER,
            positions_unchanged INTEGER,
            turnover_rate NUMERIC(10,4),  -- Percentage of portfolio turned over
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (portfolio_id, rebalance_date)
        );

        -- Portfolio performance (daily/periodic tracking)
        CREATE TABLE IF NOT EXISTS portfolio_performance (
            performance_id SERIAL PRIMARY KEY,
            portfolio_id VARCHAR(50) NOT NULL REFERENCES portfolios(portfolio_id),
            date DATE NOT NULL,
            snapshot_id INTEGER REFERENCES portfolio_snapshots(snapshot_id),
            total_value NUMERIC(20,2),
            daily_return NUMERIC(10,6),
            cumulative_return NUMERIC(10,6),
            sharpe_ratio NUMERIC(10,4),
            max_drawdown NUMERIC(10,4),
            volatility NUMERIC(10,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (portfolio_id, date)
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_portfolios_strategy ON portfolios(strategy);
        CREATE INDEX IF NOT EXISTS idx_portfolios_market_cap ON portfolios(market_cap);
        CREATE INDEX IF NOT EXISTS idx_portfolios_active ON portfolios(active);

        CREATE INDEX IF NOT EXISTS idx_snapshots_portfolio_date ON portfolio_snapshots(portfolio_id, snapshot_date);
        CREATE INDEX IF NOT EXISTS idx_snapshots_date ON portfolio_snapshots(snapshot_date);

        CREATE INDEX IF NOT EXISTS idx_holdings_snapshot ON portfolio_holdings(snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_holdings_portfolio ON portfolio_holdings(portfolio_id);
        CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON portfolio_holdings(ticker);

        CREATE INDEX IF NOT EXISTS idx_rebalancing_portfolio_date ON rebalancing_events(portfolio_id, rebalance_date);

        CREATE INDEX IF NOT EXISTS idx_performance_portfolio_date ON portfolio_performance(portfolio_id, date);

        -- Comments
        COMMENT ON TABLE portfolios IS 'Portfolio definitions (8 portfolios: dividend/growth/value × market caps)';
        COMMENT ON TABLE portfolio_snapshots IS 'Point-in-time portfolio state (rebalancing snapshots)';
        COMMENT ON TABLE portfolio_holdings IS 'Individual positions within each snapshot';
        COMMENT ON TABLE rebalancing_events IS 'Portfolio rebalancing history and turnover';
        COMMENT ON TABLE portfolio_performance IS 'Daily portfolio performance metrics';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Portfolio tables created successfully")

            # Insert the 8 portfolio definitions
            insert_portfolios = """
                INSERT INTO portfolios (portfolio_id, name, strategy, market_cap, target_position_count, rebalance_frequency)
                VALUES
                    ('dividend_large', 'Dividend - Large Cap', 'dividend', 'large_cap', 15, 'annual'),
                    ('dividend_mid', 'Dividend - Mid Cap', 'dividend', 'mid_cap', 15, 'annual'),
                    ('growth_large', 'Growth - Large Cap', 'growth', 'large_cap', 15, 'quarterly'),
                    ('growth_mid', 'Growth - Mid Cap', 'growth', 'mid_cap', 15, 'quarterly'),
                    ('growth_small', 'Growth - Small Cap', 'growth', 'small_cap', 15, 'quarterly'),
                    ('value_large', 'Value - Large Cap', 'value', 'large_cap', 15, 'quarterly'),
                    ('value_mid', 'Value - Mid Cap', 'value', 'mid_cap', 15, 'quarterly'),
                    ('value_small', 'Value - Small Cap', 'value', 'small_cap', 15, 'quarterly')
                ON CONFLICT (portfolio_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    strategy = EXCLUDED.strategy,
                    market_cap = EXCLUDED.market_cap,
                    target_position_count = EXCLUDED.target_position_count,
                    rebalance_frequency = EXCLUDED.rebalance_frequency,
                    updated_at = CURRENT_TIMESTAMP;
            """
            cur.execute(insert_portfolios)
            logger.info("Portfolio definitions inserted/updated")

            # Show created tables
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name LIKE 'portfolio%'
                ORDER BY table_name;
            """
            )
            tables = cur.fetchall()
            logger.info(f"\nPortfolio tables:")
            for table in tables:
                logger.info(f"  - {table[0]}")


if __name__ == "__main__":
    create_tables()
