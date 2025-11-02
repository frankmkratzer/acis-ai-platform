"""
Financial Statement Feature Engineering - SQL Queries
Generates features from balance_sheets, income_statements, and cash_flow_statements tables

This module provides SQL query fragments that can be integrated into the main training query
to extract growth, quality, and financial health features from financial statements.
"""


def get_financial_features_sql() -> str:
    """
    Returns SQL query fragment that adds financial statement features.
    Uses LATERAL joins to get MRQ (Most Recent Quarter) and YoY (Year over Year) data.

    Returns:
        str: SQL query fragment with financial statement joins and feature calculations
    """

    return """
        -- ================================================================
        -- INCOME STATEMENT FEATURES
        -- ================================================================

        -- Most Recent Quarter (MRQ) Income Statement
        LEFT JOIN LATERAL (
            SELECT
                revenue,
                cost_of_revenue,
                gross_profit,
                operating_income,
                net_income_loss_attributable_common_shareholders as net_income,
                ebitda,
                research_development as rd_expense,
                selling_general_administrative as sga_expense,
                diluted_earnings_per_share as eps,
                diluted_shares_outstanding as shares_outstanding,
                period_end as income_period_end
            FROM income_statements
            WHERE tickers @> ARRAY[lp.ticker::text]
              AND period_end <= lp.date
              AND timeframe = 'quarterly'
            ORDER BY period_end DESC
            LIMIT 1
        ) income_mrq ON true

        -- Year-Ago Quarter (YAQ) for Growth Calculations
        LEFT JOIN LATERAL (
            SELECT
                revenue as revenue_yago,
                gross_profit as gross_profit_yago,
                operating_income as operating_income_yago,
                net_income_loss_attributable_common_shareholders as net_income_yago,
                ebitda as ebitda_yago
            FROM income_statements
            WHERE tickers @> ARRAY[lp.ticker::text]
              AND period_end <= lp.date - INTERVAL '360 days'
              AND period_end >= lp.date - INTERVAL '380 days'
              AND timeframe = 'quarterly'
            ORDER BY period_end DESC
            LIMIT 1
        ) income_yago ON true

        -- Quarter-Ago (QAQ) for Sequential Growth
        LEFT JOIN LATERAL (
            SELECT
                revenue as revenue_qago,
                net_income_loss_attributable_common_shareholders as net_income_qago
            FROM income_statements
            WHERE tickers @> ARRAY[lp.ticker::text]
              AND period_end < income_mrq.income_period_end
              AND timeframe = 'quarterly'
            ORDER BY period_end DESC
            LIMIT 1
        ) income_qago ON true

        -- Trailing Twelve Months (TTM) Aggregates
        LEFT JOIN LATERAL (
            SELECT
                SUM(revenue) as ttm_revenue,
                SUM(net_income_loss_attributable_common_shareholders) as ttm_net_income,
                SUM(ebitda) as ttm_ebitda,
                SUM(research_development) as ttm_rd
            FROM (
                SELECT *
                FROM income_statements
                WHERE tickers @> ARRAY[lp.ticker::text]
                  AND period_end <= lp.date
                  AND timeframe = 'quarterly'
                ORDER BY period_end DESC
                LIMIT 4
            ) last_4q
        ) income_ttm ON true

        -- ================================================================
        -- BALANCE SHEET FEATURES
        -- ================================================================

        -- Most Recent Quarter (MRQ) Balance Sheet
        LEFT JOIN LATERAL (
            SELECT
                total_assets,
                total_current_assets,
                total_liabilities,
                total_current_liabilities,
                total_equity,
                cash_and_equivalents,
                receivables,
                inventories,
                property_plant_equipment_net as ppe,
                goodwill,
                intangible_assets_net as intangibles,
                accounts_payable,
                debt_current as short_term_debt,
                long_term_debt_and_capital_lease_obligations as long_term_debt,
                retained_earnings_deficit as retained_earnings,
                period_end as balance_period_end
            FROM balance_sheets
            WHERE tickers @> ARRAY[lp.ticker::text]
              AND period_end <= lp.date
              AND timeframe = 'quarterly'
            ORDER BY period_end DESC
            LIMIT 1
        ) balance_mrq ON true

        -- Year-Ago Balance Sheet for Comparisons
        LEFT JOIN LATERAL (
            SELECT
                total_assets as total_assets_yago,
                total_equity as total_equity_yago,
                total_current_assets as current_assets_yago,
                total_current_liabilities as current_liabilities_yago,
                debt_current as short_term_debt_yago,
                long_term_debt_and_capital_lease_obligations as long_term_debt_yago,
                period_end as balance_period_end_yago
            FROM balance_sheets
            WHERE tickers @> ARRAY[lp.ticker::text]
              AND period_end <= lp.date - INTERVAL '360 days'
              AND period_end >= lp.date - INTERVAL '380 days'
              AND timeframe = 'quarterly'
            ORDER BY period_end DESC
            LIMIT 1
        ) balance_yago ON true

        -- ================================================================
        -- CASH FLOW STATEMENT FEATURES
        -- ================================================================

        -- Most Recent Quarter (MRQ) Cash Flow
        LEFT JOIN LATERAL (
            SELECT
                net_cash_from_operating_activities as operating_cash_flow,
                purchase_of_property_plant_and_equipment as capex,
                net_income,
                depreciation_depletion_and_amortization as depreciation,
                dividends,
                long_term_debt_issuances_repayments as debt_issuance_repayment,
                period_end as cashflow_period_end
            FROM cash_flow_statements
            WHERE tickers @> ARRAY[lp.ticker::text]
              AND period_end <= lp.date
              AND timeframe = 'quarterly'
            ORDER BY period_end DESC
            LIMIT 1
        ) cashflow_mrq ON true

        -- TTM Operating Cash Flow
        LEFT JOIN LATERAL (
            SELECT
                SUM(net_cash_from_operating_activities) as ttm_operating_cash_flow,
                SUM(ABS(COALESCE(purchase_of_property_plant_and_equipment, 0))) as ttm_capex
            FROM (
                SELECT *
                FROM cash_flow_statements
                WHERE tickers @> ARRAY[lp.ticker::text]
                  AND period_end <= lp.date
                  AND timeframe = 'quarterly'
                ORDER BY period_end DESC
                LIMIT 4
            ) last_4q
        ) cashflow_ttm ON true
    """


def get_calculated_features() -> str:
    """
    Returns SQL SELECT fragment with calculated features from financial statement data.
    These features are computed from the joined tables above.

    Returns:
        str: SQL SELECT fragment with feature calculations
    """

    return """
                -- ============================================================
                -- GROWTH & MOMENTUM FEATURES
                -- ============================================================

                -- Revenue Growth
                (income_mrq.revenue / NULLIF(income_yago.revenue_yago, 0) - 1) as revenue_growth_yoy,
                (income_mrq.revenue / NULLIF(income_qago.revenue_qago, 0) - 1) as revenue_growth_qoq,

                -- Earnings Growth
                (income_mrq.net_income / NULLIF(income_yago.net_income_yago, 0) - 1) as earnings_growth_yoy,
                (income_mrq.net_income / NULLIF(income_qago.net_income_qago, 0) - 1) as earnings_growth_qoq,

                -- EBITDA Growth
                (income_mrq.ebitda / NULLIF(income_yago.ebitda_yago, 0) - 1) as ebitda_growth_yoy,

                -- ============================================================
                -- PROFITABILITY & MARGIN FEATURES
                -- ============================================================

                -- Margins (MRQ)
                (income_mrq.gross_profit / NULLIF(income_mrq.revenue, 0)) as gross_margin,
                (income_mrq.operating_income / NULLIF(income_mrq.revenue, 0)) as operating_margin,
                (income_mrq.net_income / NULLIF(income_mrq.revenue, 0)) as net_margin,
                (income_mrq.ebitda / NULLIF(income_mrq.revenue, 0)) as ebitda_margin,

                -- Margin Expansion (YoY Change)
                ((income_mrq.gross_profit / NULLIF(income_mrq.revenue, 0)) -
                 (income_yago.gross_profit_yago / NULLIF(income_yago.revenue_yago, 0))) as gross_margin_expansion,
                ((income_mrq.operating_income / NULLIF(income_mrq.revenue, 0)) -
                 (income_yago.operating_income_yago / NULLIF(income_yago.revenue_yago, 0))) as operating_margin_expansion,

                -- Return Metrics (TTM)
                (income_ttm.ttm_net_income / NULLIF(balance_mrq.total_assets, 0)) as roa_ttm,
                (income_ttm.ttm_net_income / NULLIF(balance_mrq.total_equity, 0)) as roe_ttm,

                -- R&D Intensity
                (income_mrq.rd_expense / NULLIF(income_mrq.revenue, 0)) as rd_to_sales,
                (income_ttm.ttm_rd / NULLIF(income_ttm.ttm_revenue, 0)) as rd_to_sales_ttm,

                -- ============================================================
                -- CASH FLOW QUALITY FEATURES
                -- ============================================================

                -- Operating Cash Flow Margins
                (cashflow_mrq.operating_cash_flow / NULLIF(income_mrq.revenue, 0)) as ocf_margin,
                (cashflow_ttm.ttm_operating_cash_flow / NULLIF(income_ttm.ttm_revenue, 0)) as ocf_margin_ttm,

                -- Free Cash Flow
                (cashflow_mrq.operating_cash_flow + COALESCE(cashflow_mrq.capex, 0)) as free_cash_flow_mrq,
                (cashflow_ttm.ttm_operating_cash_flow - COALESCE(cashflow_ttm.ttm_capex, 0)) as free_cash_flow_ttm,
                ((cashflow_ttm.ttm_operating_cash_flow - COALESCE(cashflow_ttm.ttm_capex, 0)) /
                 NULLIF(income_ttm.ttm_revenue, 0)) as fcf_margin_ttm,

                -- Cash Conversion (Quality of Earnings)
                (cashflow_mrq.operating_cash_flow / NULLIF(cashflow_mrq.net_income, 0)) as cash_conversion_rate,
                (cashflow_ttm.ttm_operating_cash_flow / NULLIF(income_ttm.ttm_net_income, 0)) as cash_conversion_rate_ttm,

                -- Accruals Ratio (Lower = Higher Quality)
                ((cashflow_mrq.net_income - cashflow_mrq.operating_cash_flow) /
                 NULLIF(balance_mrq.total_assets, 0)) as accruals_ratio,

                -- CapEx Intensity
                (ABS(COALESCE(cashflow_mrq.capex, 0)) / NULLIF(income_mrq.revenue, 0)) as capex_to_sales,
                (ABS(COALESCE(cashflow_mrq.capex, 0)) / NULLIF(cashflow_mrq.depreciation, 0)) as capex_to_depreciation,

                -- ============================================================
                -- FINANCIAL HEALTH FEATURES
                -- ============================================================

                -- Leverage Ratios
                ((COALESCE(balance_mrq.short_term_debt, 0) + COALESCE(balance_mrq.long_term_debt, 0)) /
                 NULLIF(balance_mrq.total_equity, 0)) as debt_to_equity,
                ((COALESCE(balance_mrq.short_term_debt, 0) + COALESCE(balance_mrq.long_term_debt, 0)) /
                 NULLIF(balance_mrq.total_assets, 0)) as debt_to_assets,

                -- Interest Coverage (using EBITDA as proxy since interest expense may not be available)
                (income_mrq.ebitda / NULLIF(GREATEST(income_mrq.revenue * 0.01, 1), 0)) as ebitda_coverage_proxy,

                -- Liquidity Ratios
                (balance_mrq.total_current_assets / NULLIF(balance_mrq.total_current_liabilities, 0)) as current_ratio,
                ((balance_mrq.total_current_assets - COALESCE(balance_mrq.inventories, 0)) /
                 NULLIF(balance_mrq.total_current_liabilities, 0)) as quick_ratio,
                (balance_mrq.cash_and_equivalents / NULLIF(balance_mrq.total_current_liabilities, 0)) as cash_ratio,

                -- Working Capital
                (balance_mrq.total_current_assets - balance_mrq.total_current_liabilities) as working_capital,
                ((balance_mrq.total_current_assets - balance_mrq.total_current_liabilities) /
                 NULLIF(income_mrq.revenue, 0)) as working_capital_to_sales,

                -- Balance Sheet Strength
                (balance_mrq.total_equity / NULLIF(balance_mrq.total_assets, 0)) as equity_ratio,
                (balance_mrq.cash_and_equivalents / NULLIF(balance_mrq.total_assets, 0)) as cash_to_assets,

                -- Asset Efficiency
                (income_mrq.revenue / NULLIF(balance_mrq.total_assets, 0)) as asset_turnover,
                (income_ttm.ttm_revenue / NULLIF(balance_mrq.total_assets, 0)) as asset_turnover_ttm,

                -- ============================================================
                -- PIOTROSKI F-SCORE COMPONENTS
                -- ============================================================

                -- Profitability Signals (4 points)
                CASE WHEN income_mrq.net_income > 0 THEN 1 ELSE 0 END as f_profitable,
                CASE WHEN cashflow_mrq.operating_cash_flow > 0 THEN 1 ELSE 0 END as f_cfo_positive,
                CASE WHEN (income_ttm.ttm_net_income / NULLIF(balance_mrq.total_assets, 0)) >
                          (income_yago.net_income_yago / NULLIF(balance_yago.total_assets_yago, 0)) THEN 1 ELSE 0 END as f_roa_increase,
                CASE WHEN cashflow_mrq.operating_cash_flow > income_mrq.net_income THEN 1 ELSE 0 END as f_quality_earnings,

                -- Leverage & Liquidity Signals (3 points)
                CASE WHEN (COALESCE(balance_mrq.short_term_debt, 0) + COALESCE(balance_mrq.long_term_debt, 0)) <
                          (COALESCE(balance_yago.short_term_debt_yago, 0) + COALESCE(balance_yago.long_term_debt_yago, 0)) THEN 1 ELSE 0 END as f_leverage_decrease,
                CASE WHEN (balance_mrq.total_current_assets / NULLIF(balance_mrq.total_current_liabilities, 0)) >
                          (balance_yago.current_assets_yago / NULLIF(balance_yago.current_liabilities_yago, 0)) THEN 1 ELSE 0 END as f_liquidity_increase,

                -- Operating Efficiency Signals (2 points)
                CASE WHEN (income_mrq.gross_profit / NULLIF(income_mrq.revenue, 0)) >
                          (income_yago.gross_profit_yago / NULLIF(income_yago.revenue_yago, 0)) THEN 1 ELSE 0 END as f_margin_increase,
                CASE WHEN (income_mrq.revenue / NULLIF(balance_mrq.total_assets, 0)) >
                          (income_yago.revenue_yago / NULLIF(balance_yago.total_assets_yago, 0)) THEN 1 ELSE 0 END as f_turnover_increase,

                -- TTM Metrics (useful for valuation)
                income_ttm.ttm_revenue,
                income_ttm.ttm_net_income,
                income_ttm.ttm_ebitda,
                cashflow_ttm.ttm_operating_cash_flow,
                (cashflow_ttm.ttm_operating_cash_flow - COALESCE(cashflow_ttm.ttm_capex, 0)) as ttm_free_cash_flow
    """


def get_feature_list() -> list:
    """
    Returns list of all feature column names that will be added to the dataset.
    This is useful for tracking features and feature importance analysis.

    Returns:
        list: List of feature names
    """
    return [
        # Growth features
        "revenue_growth_yoy",
        "revenue_growth_qoq",
        "earnings_growth_yoy",
        "earnings_growth_qoq",
        "ebitda_growth_yoy",
        # Margin features
        "gross_margin",
        "operating_margin",
        "net_margin",
        "ebitda_margin",
        "gross_margin_expansion",
        "operating_margin_expansion",
        "roa_ttm",
        "roe_ttm",
        "rd_to_sales",
        "rd_to_sales_ttm",
        # Cash flow quality
        "ocf_margin",
        "ocf_margin_ttm",
        "free_cash_flow_mrq",
        "free_cash_flow_ttm",
        "fcf_margin_ttm",
        "cash_conversion_rate",
        "cash_conversion_rate_ttm",
        "accruals_ratio",
        "capex_to_sales",
        "capex_to_depreciation",
        # Financial health
        "debt_to_equity",
        "debt_to_assets",
        "ebitda_coverage_proxy",
        "current_ratio",
        "quick_ratio",
        "cash_ratio",
        "working_capital",
        "working_capital_to_sales",
        "equity_ratio",
        "cash_to_assets",
        "asset_turnover",
        "asset_turnover_ttm",
        # Piotroski F-Score components
        "f_profitable",
        "f_cfo_positive",
        "f_roa_increase",
        "f_quality_earnings",
        "f_leverage_decrease",
        "f_liquidity_increase",
        "f_margin_increase",
        "f_turnover_increase",
        # TTM aggregates
        "ttm_revenue",
        "ttm_net_income",
        "ttm_ebitda",
        "ttm_operating_cash_flow",
        "ttm_free_cash_flow",
    ]
