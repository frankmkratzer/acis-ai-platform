'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Database, Table, FileText, X } from 'lucide-react'

// Complete table schema definitions for all 47 tables
const tableSchemas: Record<string, Array<{name: string, type: string, nullable: string}>> = {
  auto_training_log: [
    { name: 'model_name', type: 'varchar(100)', nullable: 'NO' },
    { name: 'strategy', type: 'varchar(50)', nullable: 'NO' },
    { name: 'market_cap', type: 'varchar(20)', nullable: 'YES' },
    { name: 'status', type: 'varchar(20)', nullable: 'NO' },
    { name: 'duration_minutes', type: 'numeric(10,2)', nullable: 'YES' },
    { name: 'error_message', type: 'text', nullable: 'YES' },
    { name: 'trained_at', type: 'timestamp without time zone', nullable: 'NO' },
  ],
  backtest_results: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'rl_portfolio_id', type: 'integer', nullable: 'NO' },
    { name: 'rl_portfolio_name', type: 'varchar(100)', nullable: 'NO' },
    { name: 'model_path', type: 'varchar(500)', nullable: 'NO' },
    { name: 'start_date', type: 'date', nullable: 'NO' },
    { name: 'end_date', type: 'date', nullable: 'NO' },
    { name: 'initial_capital', type: 'numeric(20,2)', nullable: 'NO' },
    { name: 'final_value', type: 'numeric(20,2)', nullable: 'NO' },
    { name: 'total_return', type: 'numeric(10,4)', nullable: 'NO' },
    { name: 'annualized_return', type: 'numeric(10,4)', nullable: 'NO' },
    { name: 'sharpe_ratio', type: 'numeric(10,4)', nullable: 'YES' },
    { name: 'max_drawdown', type: 'numeric(10,4)', nullable: 'YES' },
    { name: 'num_trades', type: 'integer', nullable: 'YES' },
    { name: 'avg_turnover', type: 'numeric(5,4)', nullable: 'YES' },
    { name: 'trades_file', type: 'varchar(500)', nullable: 'YES' },
    { name: 'positions_file', type: 'varchar(500)', nullable: 'YES' },
    { name: 'rebalance_file', type: 'varchar(500)', nullable: 'YES' },
    { name: 'report_file', type: 'varchar(500)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  balance_sheets: [
    { name: 'cik', type: 'varchar(20)', nullable: 'NO' },
    { name: 'period_end', type: 'date', nullable: 'NO' },
    { name: 'timeframe', type: 'varchar(10)', nullable: 'NO' },
    { name: 'filing_date', type: 'date', nullable: 'YES' },
    { name: 'fiscal_quarter', type: 'integer', nullable: 'YES' },
    { name: 'fiscal_year', type: 'integer', nullable: 'YES' },
    { name: 'tickers', type: 'ARRAY', nullable: 'YES' },
    { name: 'accounts_payable', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'accrued_and_other_current_liabilities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'accumulated_other_comprehensive_income', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'additional_paid_in_capital', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'cash_and_equivalents', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'commitments_and_contingencies', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'common_stock', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'debt_current', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'deferred_revenue_current', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'goodwill', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'intangible_assets_net', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'inventories', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'long_term_debt_and_capital_lease_obligations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'noncontrolling_interest', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_assets', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_current_assets', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_equity', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_noncurrent_liabilities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'preferred_stock', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'property_plant_equipment_net', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'receivables', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'retained_earnings_deficit', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'short_term_investments', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_assets', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_current_assets', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_current_liabilities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_equity', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_equity_attributable_to_parent', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_liabilities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_liabilities_and_equity', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'treasury_stock', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  brokerage_oauth_tokens: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'client_id', type: 'integer', nullable: 'NO' },
    { name: 'brokerage_id', type: 'integer', nullable: 'NO' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'access_token', type: 'text', nullable: 'NO' },
    { name: 'refresh_token', type: 'text', nullable: 'NO' },
    { name: 'token_type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'scope', type: 'text', nullable: 'YES' },
    { name: 'expires_at', type: 'timestamp without time zone', nullable: 'NO' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  brokerages: [
    { name: 'brokerage_id', type: 'integer', nullable: 'NO' },
    { name: 'name', type: 'varchar(50)', nullable: 'NO' },
    { name: 'display_name', type: 'varchar(100)', nullable: 'NO' },
    { name: 'supports_live_trading', type: 'boolean', nullable: 'YES' },
    { name: 'supports_paper_trading', type: 'boolean', nullable: 'YES' },
    { name: 'api_type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'status', type: 'varchar(20)', nullable: 'YES' },
    { name: 'config_template', type: 'jsonb', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  cash_flow_statements: [
    { name: 'cik', type: 'varchar(20)', nullable: 'NO' },
    { name: 'period_end', type: 'date', nullable: 'NO' },
    { name: 'timeframe', type: 'varchar(10)', nullable: 'NO' },
    { name: 'filing_date', type: 'date', nullable: 'YES' },
    { name: 'fiscal_quarter', type: 'integer', nullable: 'YES' },
    { name: 'fiscal_year', type: 'integer', nullable: 'YES' },
    { name: 'tickers', type: 'ARRAY', nullable: 'YES' },
    { name: 'cash_from_operating_activities_continuing_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_operating_activities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_operating_activities_discontinued_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'change_in_other_operating_assets_and_liabilities_net', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_operating_activities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_investing_activities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_investing_activities_continuing_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_investing_activities_discontinued_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'purchase_of_property_plant_and_equipment', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'sale_of_property_plant_and_equipment', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_investing_activities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_financing_activities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_financing_activities_continuing_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_cash_from_financing_activities_discontinued_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'dividends', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'long_term_debt_issuances_repayments', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'short_term_debt_issuances_repayments', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_financing_activities', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_income', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'depreciation_depletion_and_amortization', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'change_in_cash_and_equivalents', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'effect_of_currency_exchange_rate', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'income_loss_from_discontinued_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'noncontrolling_interests', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_cash_adjustments', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  client_brokerage_accounts: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'client_id', type: 'integer', nullable: 'NO' },
    { name: 'brokerage_id', type: 'integer', nullable: 'NO' },
    { name: 'account_number', type: 'varchar(255)', nullable: 'NO' },
    { name: 'account_type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'is_active', type: 'boolean', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'account_hash', type: 'varchar(255)', nullable: 'YES' },
  ],
  client_rl_portfolio_assignments: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'client_id', type: 'integer', nullable: 'NO' },
    { name: 'account_id', type: 'integer', nullable: 'NO' },
    { name: 'rl_portfolio_id', type: 'integer', nullable: 'NO' },
    { name: 'rl_portfolio_name', type: 'varchar(100)', nullable: 'NO' },
    { name: 'allocation_percent', type: 'numeric(5,2)', nullable: 'NO' },
    { name: 'auto_rebalance', type: 'boolean', nullable: 'YES' },
    { name: 'rebalance_frequency', type: 'varchar(20)', nullable: 'YES' },
    { name: 'is_active', type: 'boolean', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  clients: [
    { name: 'client_id', type: 'integer', nullable: 'NO' },
    { name: 'client_name', type: 'varchar(255)', nullable: 'NO' },
    { name: 'email', type: 'varchar(255)', nullable: 'YES' },
    { name: 'phone', type: 'varchar(50)', nullable: 'YES' },
    { name: 'client_type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'status', type: 'varchar(50)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'is_admin', type: 'boolean', nullable: 'YES' },
    { name: 'password_hash', type: 'varchar(255)', nullable: 'YES' },
    { name: 'is_active', type: 'boolean', nullable: 'YES' },
    { name: 'first_name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'last_name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'auto_trading_enabled', type: 'boolean', nullable: 'YES' },
    { name: 'risk_tolerance', type: 'varchar(20)', nullable: 'YES' },
    { name: 'rebalance_frequency', type: 'varchar(20)', nullable: 'YES' },
    { name: 'drift_threshold', type: 'numeric(5,4)', nullable: 'YES' },
    { name: 'max_position_size', type: 'numeric(5,4)', nullable: 'YES' },
    { name: 'allowed_strategies', type: 'ARRAY', nullable: 'YES' },
    { name: 'min_cash_balance', type: 'numeric(12,2)', nullable: 'YES' },
    { name: 'tax_optimization_enabled', type: 'boolean', nullable: 'YES' },
    { name: 'esg_preferences', type: 'jsonb', nullable: 'YES' },
    { name: 'sector_limits', type: 'jsonb', nullable: 'YES' },
    { name: 'trading_mode', type: 'varchar(20)', nullable: 'YES' },
    { name: 'date_of_birth', type: 'date', nullable: 'YES' },
  ],
  daily_bars: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'open', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'high', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'low', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'close', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'volume', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'vwap', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'transactions', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  dividends: [
    { name: 'id', type: 'varchar(100)', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'cash_amount', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'currency', type: 'varchar(10)', nullable: 'YES' },
    { name: 'declaration_date', type: 'date', nullable: 'YES' },
    { name: 'dividend_type', type: 'varchar(10)', nullable: 'YES' },
    { name: 'ex_dividend_date', type: 'date', nullable: 'YES' },
    { name: 'frequency', type: 'integer', nullable: 'YES' },
    { name: 'pay_date', type: 'date', nullable: 'YES' },
    { name: 'record_date', type: 'date', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  ema: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'window_size', type: 'integer', nullable: 'NO' },
    { name: 'series_type', type: 'varchar(20)', nullable: 'NO' },
    { name: 'timespan', type: 'varchar(20)', nullable: 'NO' },
    { name: 'value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  etf_bars: [
    { name: 'ticker', type: 'varchar(10)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'open', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'high', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'low', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'close', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'volume', type: 'bigint', nullable: 'YES' },
    { name: 'vwap', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'transactions', type: 'integer', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  exchanges: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'exchange_id', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'acronym', type: 'varchar(50)', nullable: 'YES' },
    { name: 'asset_class', type: 'varchar(50)', nullable: 'YES' },
    { name: 'locale', type: 'varchar(50)', nullable: 'YES' },
    { name: 'mic', type: 'varchar(20)', nullable: 'YES' },
    { name: 'name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'operating_mic', type: 'varchar(20)', nullable: 'YES' },
    { name: 'participant_id', type: 'varchar(50)', nullable: 'YES' },
    { name: 'type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'url', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  income_statements: [
    { name: 'cik', type: 'varchar(20)', nullable: 'NO' },
    { name: 'period_end', type: 'date', nullable: 'NO' },
    { name: 'timeframe', type: 'varchar(10)', nullable: 'NO' },
    { name: 'filing_date', type: 'date', nullable: 'YES' },
    { name: 'fiscal_quarter', type: 'integer', nullable: 'YES' },
    { name: 'fiscal_year', type: 'integer', nullable: 'YES' },
    { name: 'tickers', type: 'ARRAY', nullable: 'YES' },
    { name: 'revenue', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'cost_of_revenue', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'gross_profit', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'research_development', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'selling_general_administrative', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_operating_expenses', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_operating_expenses', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'operating_income', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'interest_income', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'interest_expense', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'other_income_expense', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_other_income_expense', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'income_before_income_taxes', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'income_taxes', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'consolidated_net_income_loss', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'net_income_loss_attributable_common_shareholders', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'noncontrolling_interest', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'discontinued_operations', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'extraordinary_items', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'preferred_stock_dividends_declared', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'equity_in_affiliates', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'basic_earnings_per_share', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'basic_shares_outstanding', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'diluted_earnings_per_share', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'diluted_shares_outstanding', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'ebitda', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'depreciation_depletion_amortization', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  ipos: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'issuer_name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'isin', type: 'varchar(20)', nullable: 'YES' },
    { name: 'listing_date', type: 'date', nullable: 'NO' },
    { name: 'ipo_status', type: 'varchar(50)', nullable: 'YES' },
    { name: 'final_issue_price', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'lowest_offer_price', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'highest_offer_price', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'min_shares_offered', type: 'bigint', nullable: 'YES' },
    { name: 'max_shares_offered', type: 'bigint', nullable: 'YES' },
    { name: 'total_offer_size', type: 'numeric(20,2)', nullable: 'YES' },
    { name: 'announced_date', type: 'date', nullable: 'YES' },
    { name: 'last_updated', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'primary_exchange', type: 'varchar(20)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  latest_training_status: [
    { name: 'model_name', type: 'varchar(100)', nullable: 'YES' },
    { name: 'strategy', type: 'varchar(50)', nullable: 'YES' },
    { name: 'market_cap', type: 'varchar(20)', nullable: 'YES' },
    { name: 'status', type: 'varchar(20)', nullable: 'YES' },
    { name: 'duration_minutes', type: 'numeric(10,2)', nullable: 'YES' },
    { name: 'trained_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  macd: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'short_window', type: 'integer', nullable: 'NO' },
    { name: 'long_window', type: 'integer', nullable: 'NO' },
    { name: 'signal_window', type: 'integer', nullable: 'NO' },
    { name: 'series_type', type: 'varchar(20)', nullable: 'NO' },
    { name: 'timespan', type: 'varchar(20)', nullable: 'NO' },
    { name: 'macd_value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'signal_value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'histogram_value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  market_holidays: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'exchange', type: 'varchar(50)', nullable: 'YES' },
    { name: 'name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'status', type: 'varchar(20)', nullable: 'YES' },
    { name: 'open', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'close', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  market_regime: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'vix', type: 'numeric(6,2)', nullable: 'YES' },
    { name: 'realized_volatility_20d', type: 'numeric(8,4)', nullable: 'YES' },
    { name: 'volatility_regime', type: 'varchar(20)', nullable: 'YES' },
    { name: 'spy_sma_50', type: 'numeric(10,2)', nullable: 'YES' },
    { name: 'spy_sma_200', type: 'numeric(10,2)', nullable: 'YES' },
    { name: 'trend_regime', type: 'varchar(20)', nullable: 'YES' },
    { name: 'advance_decline_ratio', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'new_highs_lows_ratio', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'sector_momentum', type: 'jsonb', nullable: 'YES' },
    { name: 'treasury_10y', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'treasury_2y', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'yield_curve_slope', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'regime_label', type: 'varchar(50)', nullable: 'YES' },
    { name: 'regime_confidence', type: 'numeric(4,3)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  meta_strategy_selection: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'strategy_probabilities', type: 'jsonb', nullable: 'YES' },
    { name: 'selected_strategy', type: 'varchar(50)', nullable: 'YES' },
    { name: 'selection_confidence', type: 'numeric(4,3)', nullable: 'YES' },
    { name: 'market_regime', type: 'varchar(50)', nullable: 'YES' },
    { name: 'recent_performance', type: 'jsonb', nullable: 'YES' },
    { name: 'model_version', type: 'varchar(50)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  model_deployment_log: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'model_version_id', type: 'integer', nullable: 'NO' },
    { name: 'action', type: 'varchar(50)', nullable: 'NO' },
    { name: 'previous_status', type: 'varchar(50)', nullable: 'YES' },
    { name: 'new_status', type: 'varchar(50)', nullable: 'YES' },
    { name: 'performed_by', type: 'varchar(100)', nullable: 'YES' },
    { name: 'performed_at', type: 'timestamp without time zone', nullable: 'NO' },
    { name: 'reason', type: 'text', nullable: 'YES' },
    { name: 'metadata', type: 'jsonb', nullable: 'YES' },
  ],
  model_evaluation_history: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'model_version_id', type: 'integer', nullable: 'NO' },
    { name: 'evaluated_at', type: 'timestamp without time zone', nullable: 'NO' },
    { name: 'evaluation_period_start', type: 'date', nullable: 'YES' },
    { name: 'evaluation_period_end', type: 'date', nullable: 'YES' },
    { name: 'spearman_ic', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'pearson_correlation', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'rmse', type: 'numeric(15,6)', nullable: 'YES' },
    { name: 'mae', type: 'numeric(15,6)', nullable: 'YES' },
    { name: 'metrics', type: 'jsonb', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'NO' },
  ],
  model_versions: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'model_name', type: 'varchar(255)', nullable: 'NO' },
    { name: 'version', type: 'varchar(50)', nullable: 'NO' },
    { name: 'framework', type: 'varchar(50)', nullable: 'NO' },
    { name: 'trained_at', type: 'timestamp without time zone', nullable: 'NO' },
    { name: 'training_config', type: 'jsonb', nullable: 'YES' },
    { name: 'training_duration_seconds', type: 'integer', nullable: 'YES' },
    { name: 'training_start_date', type: 'date', nullable: 'YES' },
    { name: 'training_end_date', type: 'date', nullable: 'YES' },
    { name: 'n_training_samples', type: 'bigint', nullable: 'YES' },
    { name: 'n_features', type: 'integer', nullable: 'YES' },
    { name: 'spearman_ic', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'pearson_correlation', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'train_rmse', type: 'numeric(15,6)', nullable: 'YES' },
    { name: 'val_rmse', type: 'numeric(15,6)', nullable: 'YES' },
    { name: 'additional_metrics', type: 'jsonb', nullable: 'YES' },
    { name: 'model_path', type: 'varchar(500)', nullable: 'NO' },
    { name: 'size_mb', type: 'numeric(10,2)', nullable: 'YES' },
    { name: 'status', type: 'varchar(50)', nullable: 'NO' },
    { name: 'is_production', type: 'boolean', nullable: 'NO' },
    { name: 'promoted_to_production_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'description', type: 'text', nullable: 'YES' },
    { name: 'created_by', type: 'varchar(100)', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'tags', type: 'ARRAY', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'NO' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'NO' },
  ],
  news: [
    { name: 'article_id', type: 'varchar(255)', nullable: 'NO' },
    { name: 'title', type: 'text', nullable: 'YES' },
    { name: 'author', type: 'varchar(255)', nullable: 'YES' },
    { name: 'published_utc', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'article_url', type: 'text', nullable: 'YES' },
    { name: 'image_url', type: 'text', nullable: 'YES' },
    { name: 'description', type: 'text', nullable: 'YES' },
    { name: 'tickers', type: 'ARRAY', nullable: 'YES' },
    { name: 'publisher_name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'publisher_homepage_url', type: 'text', nullable: 'YES' },
    { name: 'publisher_logo_url', type: 'text', nullable: 'YES' },
    { name: 'keywords', type: 'ARRAY', nullable: 'YES' },
    { name: 'sentiment', type: 'varchar(20)', nullable: 'YES' },
    { name: 'sentiment_reasoning', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  paper_accounts: [
    { name: 'account_id', type: 'varchar(100)', nullable: 'NO' },
    { name: 'cash_balance', type: 'numeric(15,2)', nullable: 'NO' },
    { name: 'buying_power', type: 'numeric(15,2)', nullable: 'NO' },
    { name: 'total_value', type: 'numeric(15,2)', nullable: 'NO' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  paper_positions: [
    { name: 'account_id', type: 'varchar(100)', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(50)', nullable: 'NO' },
    { name: 'quantity', type: 'numeric(15,4)', nullable: 'NO' },
    { name: 'avg_price', type: 'numeric(15,4)', nullable: 'NO' },
    { name: 'market_value', type: 'numeric(15,2)', nullable: 'NO' },
    { name: 'unrealized_pnl', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  portfolio_holdings: [
    { name: 'holding_id', type: 'integer', nullable: 'NO' },
    { name: 'snapshot_id', type: 'integer', nullable: 'NO' },
    { name: 'portfolio_id', type: 'varchar(50)', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'weight', type: 'numeric(10,6)', nullable: 'NO' },
    { name: 'score', type: 'numeric(20,6)', nullable: 'YES' },
    { name: 'rank', type: 'integer', nullable: 'YES' },
    { name: 'shares', type: 'integer', nullable: 'YES' },
    { name: 'entry_price', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'entry_value', type: 'numeric(20,2)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  portfolio_performance: [
    { name: 'performance_id', type: 'integer', nullable: 'NO' },
    { name: 'portfolio_id', type: 'varchar(50)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'snapshot_id', type: 'integer', nullable: 'YES' },
    { name: 'total_value', type: 'numeric(20,2)', nullable: 'YES' },
    { name: 'daily_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'cumulative_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'sharpe_ratio', type: 'numeric(10,4)', nullable: 'YES' },
    { name: 'max_drawdown', type: 'numeric(10,4)', nullable: 'YES' },
    { name: 'volatility', type: 'numeric(10,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  portfolio_positions: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'ticker', type: 'varchar(10)', nullable: 'NO' },
    { name: 'quantity', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'average_cost', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'current_price', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'market_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'cost_basis', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'unrealized_pnl', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'unrealized_pnl_pct', type: 'numeric(8,4)', nullable: 'YES' },
    { name: 'opened_date', type: 'date', nullable: 'YES' },
    { name: 'last_updated', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  portfolio_snapshots: [
    { name: 'snapshot_id', type: 'integer', nullable: 'NO' },
    { name: 'portfolio_id', type: 'varchar(50)', nullable: 'NO' },
    { name: 'snapshot_date', type: 'date', nullable: 'NO' },
    { name: 'snapshot_type', type: 'varchar(20)', nullable: 'NO' },
    { name: 'position_count', type: 'integer', nullable: 'YES' },
    { name: 'candidates_screened', type: 'integer', nullable: 'YES' },
    { name: 'total_value', type: 'numeric(20,2)', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  portfolio_value_history: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'total_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'cash_balance', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'positions_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'daily_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'cumulative_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'spy_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'alpha', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  portfolios: [
    { name: 'portfolio_id', type: 'varchar(50)', nullable: 'NO' },
    { name: 'name', type: 'varchar(100)', nullable: 'NO' },
    { name: 'strategy', type: 'varchar(20)', nullable: 'NO' },
    { name: 'market_cap', type: 'varchar(20)', nullable: 'NO' },
    { name: 'target_position_count', type: 'integer', nullable: 'YES' },
    { name: 'rebalance_frequency', type: 'varchar(20)', nullable: 'NO' },
    { name: 'active', type: 'boolean', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  ratios: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'cik', type: 'varchar(20)', nullable: 'YES' },
    { name: 'price', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'market_cap', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'enterprise_value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'average_volume', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'price_to_earnings', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'price_to_book', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'price_to_sales', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'price_to_cash_flow', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'price_to_free_cash_flow', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'ev_to_sales', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'ev_to_ebitda', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'earnings_per_share', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'return_on_assets', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'return_on_equity', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'dividend_yield', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'current', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'quick', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'cash', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'debt_to_equity', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'free_cash_flow', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  rebalancing_events: [
    { name: 'event_id', type: 'integer', nullable: 'NO' },
    { name: 'portfolio_id', type: 'varchar(50)', nullable: 'NO' },
    { name: 'rebalance_date', type: 'date', nullable: 'NO' },
    { name: 'prev_snapshot_id', type: 'integer', nullable: 'YES' },
    { name: 'new_snapshot_id', type: 'integer', nullable: 'YES' },
    { name: 'positions_added', type: 'integer', nullable: 'YES' },
    { name: 'positions_removed', type: 'integer', nullable: 'YES' },
    { name: 'positions_unchanged', type: 'integer', nullable: 'YES' },
    { name: 'turnover_rate', type: 'numeric(10,4)', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  rebalancing_log: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'rebalance_date', type: 'date', nullable: 'NO' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'strategy_selected', type: 'varchar(50)', nullable: 'YES' },
    { name: 'meta_model_confidence', type: 'numeric(4,3)', nullable: 'YES' },
    { name: 'market_regime', type: 'varchar(50)', nullable: 'YES' },
    { name: 'pre_rebalance_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'post_rebalance_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'num_positions_before', type: 'integer', nullable: 'YES' },
    { name: 'num_positions_after', type: 'integer', nullable: 'YES' },
    { name: 'num_buys', type: 'integer', nullable: 'YES' },
    { name: 'num_sells', type: 'integer', nullable: 'YES' },
    { name: 'total_turnover', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'total_transaction_costs', type: 'numeric(12,2)', nullable: 'YES' },
    { name: 'trades', type: 'jsonb', nullable: 'YES' },
    { name: 'status', type: 'varchar(20)', nullable: 'YES' },
    { name: 'execution_time_seconds', type: 'numeric(8,2)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  risk_alerts: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'alert_date', type: 'date', nullable: 'YES' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'alert_type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'severity', type: 'varchar(20)', nullable: 'YES' },
    { name: 'message', type: 'text', nullable: 'YES' },
    { name: 'current_drawdown', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'portfolio_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'positions_affected', type: 'jsonb', nullable: 'YES' },
    { name: 'acknowledged', type: 'boolean', nullable: 'YES' },
    { name: 'resolved', type: 'boolean', nullable: 'YES' },
    { name: 'resolution_notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  rl_training_jobs: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'rl_portfolio_id', type: 'integer', nullable: 'NO' },
    { name: 'rl_portfolio_name', type: 'varchar(100)', nullable: 'NO' },
    { name: 'status', type: 'varchar(50)', nullable: 'NO' },
    { name: 'timesteps', type: 'integer', nullable: 'NO' },
    { name: 'start_date', type: 'date', nullable: 'NO' },
    { name: 'end_date', type: 'date', nullable: 'NO' },
    { name: 'progress', type: 'numeric(5,2)', nullable: 'YES' },
    { name: 'current_step', type: 'integer', nullable: 'YES' },
    { name: 'metrics', type: 'jsonb', nullable: 'YES' },
    { name: 'model_path', type: 'varchar(500)', nullable: 'YES' },
    { name: 'log_path', type: 'varchar(500)', nullable: 'YES' },
    { name: 'error_message', type: 'text', nullable: 'YES' },
    { name: 'started_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'completed_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  rsi: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'window_size', type: 'integer', nullable: 'NO' },
    { name: 'series_type', type: 'varchar(20)', nullable: 'NO' },
    { name: 'timespan', type: 'varchar(20)', nullable: 'NO' },
    { name: 'value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  short_interest: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'settlement_date', type: 'date', nullable: 'NO' },
    { name: 'short_interest', type: 'bigint', nullable: 'YES' },
    { name: 'avg_daily_volume', type: 'bigint', nullable: 'YES' },
    { name: 'days_to_cover', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  sma: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'window_size', type: 'integer', nullable: 'NO' },
    { name: 'series_type', type: 'varchar(20)', nullable: 'NO' },
    { name: 'timespan', type: 'varchar(20)', nullable: 'NO' },
    { name: 'value', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  splits: [
    { name: 'id', type: 'varchar(100)', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'execution_date', type: 'date', nullable: 'YES' },
    { name: 'split_from', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'split_to', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  strategy_performance: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'date', type: 'date', nullable: 'NO' },
    { name: 'strategy', type: 'varchar(50)', nullable: 'NO' },
    { name: 'daily_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'portfolio_value', type: 'numeric(15,2)', nullable: 'YES' },
    { name: 'num_positions', type: 'integer', nullable: 'YES' },
    { name: 'sharpe_ratio_30d', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'max_drawdown_30d', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'win_rate_30d', type: 'numeric(4,3)', nullable: 'YES' },
    { name: 'volatility_30d', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'beta', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'outperformance_vs_spy', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  strategy_rankings: [
    { name: 'strategy', type: 'varchar(50)', nullable: 'YES' },
    { name: 'daily_return', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'sharpe_ratio_30d', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'max_drawdown_30d', type: 'numeric(6,4)', nullable: 'YES' },
    { name: 'win_rate_30d', type: 'numeric(4,3)', nullable: 'YES' },
    { name: 'outperformance_vs_spy', type: 'numeric(10,6)', nullable: 'YES' },
    { name: 'sharpe_rank', type: 'bigint', nullable: 'YES' },
    { name: 'performance_rank', type: 'bigint', nullable: 'YES' },
    { name: 'date', type: 'date', nullable: 'YES' },
  ],
  ticker_events: [
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'event_date', type: 'date', nullable: 'NO' },
    { name: 'event_type', type: 'varchar(50)', nullable: 'NO' },
    { name: 'new_ticker', type: 'varchar(20)', nullable: 'YES' },
    { name: 'company_name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  ticker_overview: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'market', type: 'varchar(50)', nullable: 'YES' },
    { name: 'locale', type: 'varchar(20)', nullable: 'YES' },
    { name: 'type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'active', type: 'boolean', nullable: 'YES' },
    { name: 'currency_name', type: 'varchar(50)', nullable: 'YES' },
    { name: 'cik', type: 'varchar(20)', nullable: 'YES' },
    { name: 'composite_figi', type: 'varchar(20)', nullable: 'YES' },
    { name: 'share_class_figi', type: 'varchar(20)', nullable: 'YES' },
    { name: 'primary_exchange', type: 'varchar(50)', nullable: 'YES' },
    { name: 'description', type: 'text', nullable: 'YES' },
    { name: 'homepage_url', type: 'text', nullable: 'YES' },
    { name: 'phone_number', type: 'varchar(50)', nullable: 'YES' },
    { name: 'list_date', type: 'date', nullable: 'YES' },
    { name: 'delisted_utc', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'market_cap', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'share_class_shares_outstanding', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'weighted_shares_outstanding', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'round_lot', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'total_employees', type: 'numeric(20,4)', nullable: 'YES' },
    { name: 'sic_code', type: 'varchar(10)', nullable: 'YES' },
    { name: 'sic_description', type: 'varchar(255)', nullable: 'YES' },
    { name: 'ticker_root', type: 'varchar(20)', nullable: 'YES' },
    { name: 'ticker_suffix', type: 'varchar(20)', nullable: 'YES' },
    { name: 'address_address1', type: 'varchar(255)', nullable: 'YES' },
    { name: 'address_city', type: 'varchar(100)', nullable: 'YES' },
    { name: 'address_postal_code', type: 'varchar(20)', nullable: 'YES' },
    { name: 'address_state', type: 'varchar(50)', nullable: 'YES' },
    { name: 'branding_icon_url', type: 'text', nullable: 'YES' },
    { name: 'branding_logo_url', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  tickers: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'ticker', type: 'varchar(20)', nullable: 'NO' },
    { name: 'name', type: 'varchar(255)', nullable: 'YES' },
    { name: 'market', type: 'varchar(50)', nullable: 'YES' },
    { name: 'locale', type: 'varchar(20)', nullable: 'YES' },
    { name: 'type', type: 'varchar(50)', nullable: 'YES' },
    { name: 'active', type: 'boolean', nullable: 'YES' },
    { name: 'currency_name', type: 'varchar(50)', nullable: 'YES' },
    { name: 'cik', type: 'varchar(20)', nullable: 'YES' },
    { name: 'composite_figi', type: 'varchar(20)', nullable: 'YES' },
    { name: 'share_class_figi', type: 'varchar(20)', nullable: 'YES' },
    { name: 'primary_exchange', type: 'varchar(50)', nullable: 'YES' },
    { name: 'delisted_utc', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'last_updated_utc', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'updated_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  trade_executions: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'rebalance_id', type: 'integer', nullable: 'YES' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'ticker', type: 'varchar(10)', nullable: 'NO' },
    { name: 'side', type: 'varchar(4)', nullable: 'NO' },
    { name: 'quantity', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'target_price', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'execution_price', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'slippage', type: 'numeric(12,4)', nullable: 'YES' },
    { name: 'commission', type: 'numeric(12,2)', nullable: 'YES' },
    { name: 'sec_fee', type: 'numeric(12,2)', nullable: 'YES' },
    { name: 'total_cost', type: 'numeric(12,2)', nullable: 'YES' },
    { name: 'order_type', type: 'varchar(20)', nullable: 'YES' },
    { name: 'brokerage_order_id', type: 'varchar(100)', nullable: 'YES' },
    { name: 'execution_status', type: 'varchar(20)', nullable: 'YES' },
    { name: 'submitted_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'executed_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
  trade_recommendations: [
    { name: 'id', type: 'integer', nullable: 'NO' },
    { name: 'client_id', type: 'integer', nullable: 'NO' },
    { name: 'account_id', type: 'integer', nullable: 'YES' },
    { name: 'rl_portfolio_id', type: 'integer', nullable: 'YES' },
    { name: 'rl_portfolio_name', type: 'varchar(100)', nullable: 'YES' },
    { name: 'recommendation_type', type: 'varchar(50)', nullable: 'NO' },
    { name: 'trades', type: 'jsonb', nullable: 'NO' },
    { name: 'status', type: 'varchar(50)', nullable: 'NO' },
    { name: 'total_trades', type: 'integer', nullable: 'NO' },
    { name: 'total_buy_value', type: 'numeric(20,2)', nullable: 'YES' },
    { name: 'total_sell_value', type: 'numeric(20,2)', nullable: 'YES' },
    { name: 'expected_turnover', type: 'numeric(5,4)', nullable: 'YES' },
    { name: 'notes', type: 'text', nullable: 'YES' },
    { name: 'created_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'approved_at', type: 'timestamp without time zone', nullable: 'YES' },
    { name: 'executed_at', type: 'timestamp without time zone', nullable: 'YES' },
  ],
}


export default function DatabaseSchema() {
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleTableClick = (tableName: string) => {
    if (tableSchemas[tableName]) {
      setSelectedTable(tableName)
      setIsModalOpen(true)
    }
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setSelectedTable(null)
  }

  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Database Schema</h1>
      <p className="text-xl text-gray-600 mb-8">
        PostgreSQL database schema with 47 tables for ACIS AI platform. Click any table to view its columns.
      </p>

      {/* Client Management */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Client Management</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('clients')} className="bg-blue-50 border border-blue-200 p-3 rounded hover:bg-blue-100 transition-colors text-left cursor-pointer">
            <strong>clients</strong> - Client profiles and settings
          </button>
          <button onClick={() => handleTableClick('client_brokerage_accounts')} className="bg-blue-50 border border-blue-200 p-3 rounded hover:bg-blue-100 transition-colors text-left cursor-pointer">
            <strong>client_brokerage_accounts</strong> - Links clients to brokerage accounts
          </button>
          <button onClick={() => handleTableClick('client_rl_portfolio_assignments')} className="bg-blue-50 border border-blue-200 p-3 rounded hover:bg-blue-100 transition-colors text-left cursor-pointer">
            <strong>client_rl_portfolio_assignments</strong> - RL portfolio assignments
          </button>
          <button onClick={() => handleTableClick('brokerages')} className="bg-blue-50 border border-blue-200 p-3 rounded hover:bg-blue-100 transition-colors text-left cursor-pointer">
            <strong>brokerages</strong> - Brokerage firm details
          </button>
          <button onClick={() => handleTableClick('brokerage_oauth_tokens')} className="bg-blue-50 border border-blue-200 p-3 rounded hover:bg-blue-100 transition-colors text-left cursor-pointer">
            <strong>brokerage_oauth_tokens</strong> - OAuth tokens for API access
          </button>
        </div>
      </section>

      {/* Market Data */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Market Data</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('tickers')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>tickers</strong> - Stock symbols and metadata
          </button>
          <button onClick={() => handleTableClick('daily_bars')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>daily_bars</strong> - Historical OHLCV price data
          </button>
          <button onClick={() => handleTableClick('etf_bars')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>etf_bars</strong> - ETF price data
          </button>
          <button onClick={() => handleTableClick('ticker_overview')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>ticker_overview</strong> - Company overview information
          </button>
          <button onClick={() => handleTableClick('ticker_events')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>ticker_events</strong> - Corporate events (earnings, dividends, etc.)
          </button>
          <button onClick={() => handleTableClick('splits')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>splits</strong> - Stock split history
          </button>
          <button onClick={() => handleTableClick('dividends')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>dividends</strong> - Dividend payment history
          </button>
          <button onClick={() => handleTableClick('exchanges')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>exchanges</strong> - Stock exchange information
          </button>
          <button onClick={() => handleTableClick('market_holidays')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>market_holidays</strong> - Market closure dates
          </button>
          <button onClick={() => handleTableClick('ipos')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>ipos</strong> - Initial public offering data
          </button>
          <button onClick={() => handleTableClick('news')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>news</strong> - Market news and sentiment
          </button>
          <button onClick={() => handleTableClick('short_interest')} className="bg-green-50 border border-green-200 p-3 rounded hover:bg-green-100 transition-colors text-left cursor-pointer">
            <strong>short_interest</strong> - Short interest data
          </button>
        </div>
      </section>

      {/* Financial Statements */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Financial Statements</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('income_statements')} className="bg-purple-50 border border-purple-200 p-3 rounded hover:bg-purple-100 transition-colors text-left cursor-pointer">
            <strong>income_statements</strong> - Revenue, expenses, net income
          </button>
          <button onClick={() => handleTableClick('balance_sheets')} className="bg-purple-50 border border-purple-200 p-3 rounded hover:bg-purple-100 transition-colors text-left cursor-pointer">
            <strong>balance_sheets</strong> - Assets, liabilities, equity
          </button>
          <button onClick={() => handleTableClick('cash_flow_statements')} className="bg-purple-50 border border-purple-200 p-3 rounded hover:bg-purple-100 transition-colors text-left cursor-pointer">
            <strong>cash_flow_statements</strong> - Operating, investing, financing cash flows
          </button>
          <button onClick={() => handleTableClick('ratios')} className="bg-purple-50 border border-purple-200 p-3 rounded hover:bg-purple-100 transition-colors text-left cursor-pointer">
            <strong>ratios</strong> - Financial ratios (P/E, ROE, debt ratios, etc.)
          </button>
        </div>
      </section>

      {/* Technical Indicators */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Technical Indicators</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('sma')} className="bg-yellow-50 border border-yellow-200 p-3 rounded hover:bg-yellow-100 transition-colors text-left cursor-pointer">
            <strong>sma</strong> - Simple moving averages
          </button>
          <button onClick={() => handleTableClick('ema')} className="bg-yellow-50 border border-yellow-200 p-3 rounded hover:bg-yellow-100 transition-colors text-left cursor-pointer">
            <strong>ema</strong> - Exponential moving averages
          </button>
          <button onClick={() => handleTableClick('rsi')} className="bg-yellow-50 border border-yellow-200 p-3 rounded hover:bg-yellow-100 transition-colors text-left cursor-pointer">
            <strong>rsi</strong> - Relative strength index
          </button>
          <button onClick={() => handleTableClick('macd')} className="bg-yellow-50 border border-yellow-200 p-3 rounded hover:bg-yellow-100 transition-colors text-left cursor-pointer">
            <strong>macd</strong> - MACD indicator values
          </button>
        </div>
      </section>

      {/* Portfolio Management */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Portfolio Management</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('portfolios')} className="bg-orange-50 border border-orange-200 p-3 rounded hover:bg-orange-100 transition-colors text-left cursor-pointer">
            <strong>portfolios</strong> - Portfolio definitions
          </button>
          <button onClick={() => handleTableClick('portfolio_positions')} className="bg-orange-50 border border-orange-200 p-3 rounded hover:bg-orange-100 transition-colors text-left cursor-pointer">
            <strong>portfolio_positions</strong> - Current holdings
          </button>
          <button onClick={() => handleTableClick('portfolio_holdings')} className="bg-orange-50 border border-orange-200 p-3 rounded hover:bg-orange-100 transition-colors text-left cursor-pointer">
            <strong>portfolio_holdings</strong> - Historical holdings
          </button>
          <button onClick={() => handleTableClick('portfolio_snapshots')} className="bg-orange-50 border border-orange-200 p-3 rounded hover:bg-orange-100 transition-colors text-left cursor-pointer">
            <strong>portfolio_snapshots</strong> - Point-in-time portfolio state
          </button>
          <button onClick={() => handleTableClick('portfolio_value_history')} className="bg-orange-50 border border-orange-200 p-3 rounded hover:bg-orange-100 transition-colors text-left cursor-pointer">
            <strong>portfolio_value_history</strong> - Daily portfolio values
          </button>
          <button onClick={() => handleTableClick('portfolio_performance')} className="bg-orange-50 border border-orange-200 p-3 rounded hover:bg-orange-100 transition-colors text-left cursor-pointer">
            <strong>portfolio_performance</strong> - Performance metrics
          </button>
        </div>
      </section>

      {/* Trading */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Trading</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('trade_recommendations')} className="bg-red-50 border border-red-200 p-3 rounded hover:bg-red-100 transition-colors text-left cursor-pointer">
            <strong>trade_recommendations</strong> - AI-generated trade signals
          </button>
          <button onClick={() => handleTableClick('trade_executions')} className="bg-red-50 border border-red-200 p-3 rounded hover:bg-red-100 transition-colors text-left cursor-pointer">
            <strong>trade_executions</strong> - Executed trades log
          </button>
          <button onClick={() => handleTableClick('paper_accounts')} className="bg-red-50 border border-red-200 p-3 rounded hover:bg-red-100 transition-colors text-left cursor-pointer">
            <strong>paper_accounts</strong> - Paper trading accounts
          </button>
          <button onClick={() => handleTableClick('paper_positions')} className="bg-red-50 border border-red-200 p-3 rounded hover:bg-red-100 transition-colors text-left cursor-pointer">
            <strong>paper_positions</strong> - Paper trading positions
          </button>
          <button onClick={() => handleTableClick('rebalancing_events')} className="bg-red-50 border border-red-200 p-3 rounded hover:bg-red-100 transition-colors text-left cursor-pointer">
            <strong>rebalancing_events</strong> - Portfolio rebalancing history
          </button>
          <button onClick={() => handleTableClick('rebalancing_log')} className="bg-red-50 border border-red-200 p-3 rounded hover:bg-red-100 transition-colors text-left cursor-pointer">
            <strong>rebalancing_log</strong> - Rebalancing execution logs
          </button>
        </div>
      </section>

      {/* ML & Strategy */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">ML & Strategy</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('model_versions')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>model_versions</strong> - ML model versions and metadata
          </button>
          <button onClick={() => handleTableClick('model_evaluation_history')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>model_evaluation_history</strong> - Model performance over time
          </button>
          <button onClick={() => handleTableClick('model_deployment_log')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>model_deployment_log</strong> - Model deployment tracking
          </button>
          <button onClick={() => handleTableClick('auto_training_log')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>auto_training_log</strong> - Automated training runs
          </button>
          <button onClick={() => handleTableClick('rl_training_jobs')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>rl_training_jobs</strong> - RL agent training jobs
          </button>
          <button onClick={() => handleTableClick('backtest_results')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>backtest_results</strong> - Backtesting performance
          </button>
          <button onClick={() => handleTableClick('strategy_performance')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>strategy_performance</strong> - Strategy-level metrics
          </button>
          <button onClick={() => handleTableClick('market_regime')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>market_regime</strong> - Detected market conditions
          </button>
          <button onClick={() => handleTableClick('meta_strategy_selection')} className="bg-indigo-50 border border-indigo-200 p-3 rounded hover:bg-indigo-100 transition-colors text-left cursor-pointer">
            <strong>meta_strategy_selection</strong> - Meta-model strategy choices
          </button>
        </div>
      </section>

      {/* Risk Management */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Risk Management</h2>
        <div className="grid grid-cols-2 gap-2 not-prose text-sm">
          <button onClick={() => handleTableClick('risk_alerts')} className="bg-pink-50 border border-pink-200 p-3 rounded hover:bg-pink-100 transition-colors text-left cursor-pointer">
            <strong>risk_alerts</strong> - Risk threshold violations and alerts
          </button>
        </div>
      </section>

      {/* Key Views */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Materialized Views</h2>
        <div className="bg-gray-50 border border-gray-200 p-4 rounded not-prose text-sm">
          <p className="font-semibold mb-2">ml_training_features</p>
          <p className="text-gray-600 text-xs">
            Materialized view combining price data, fundamentals, technical indicators, and sentiment for ML model training.
            Includes 50+ features per stock-date combination.
          </p>
        </div>
      </section>

      {/* Database Commands */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Useful Commands</h2>
        <div className="space-y-3 not-prose">
          <div>
            <p className="text-sm font-semibold mb-1">List all tables:</p>
            <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs">
              PGPASSWORD=&apos;$@nJose420&apos; psql -U postgres -d acis-ai -h localhost -c &quot;\dt&quot;
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold mb-1">View table schema:</p>
            <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs">
              PGPASSWORD=&apos;$@nJose420&apos; psql -U postgres -d acis-ai -h localhost -c &quot;\d+ table_name&quot;
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold mb-1">Refresh ML features view:</p>
            <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs">
              REFRESH MATERIALIZED VIEW CONCURRENTLY ml_training_features
            </div>
          </div>
        </div>
      </section>

      {/* Summary Stats */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Summary</h2>
        <div className="grid grid-cols-3 gap-4 not-prose">
          <div className="bg-white border border-gray-200 p-4 rounded text-center">
            <p className="text-3xl font-bold text-blue-600">47</p>
            <p className="text-sm text-gray-600 mt-1">Total Tables</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded text-center">
            <p className="text-3xl font-bold text-green-600">1</p>
            <p className="text-sm text-gray-600 mt-1">Materialized View</p>
          </div>
          <div className="bg-white border border-gray-200 p-4 rounded text-center">
            <p className="text-3xl font-bold text-purple-600">PostgreSQL</p>
            <p className="text-sm text-gray-600 mt-1">Database Engine</p>
          </div>
        </div>
      </section>

      {/* Modal */}
      {isModalOpen && selectedTable && tableSchemas[selectedTable] && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={closeModal}>
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-2xl font-bold text-gray-900">{selectedTable}</h3>
              <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[calc(80vh-120px)] p-6">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Column Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nullable</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tableSchemas[selectedTable].map((column, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{column.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{column.type}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${ column.nullable === 'YES' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'}`}>
                          {column.nullable === 'YES' ? 'Yes' : 'No'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
