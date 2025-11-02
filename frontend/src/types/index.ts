/**
 * TypeScript type definitions for ACIS AI Platform API
 *
 * These types match the Pydantic schemas in backend/api/models/schemas.py
 */

// ============================================
// Client Types
// ============================================

export interface Client {
  client_id: number
  first_name: string
  last_name: string
  email: string
  phone?: string
  date_of_birth?: string
  is_active: boolean
  risk_tolerance?: string
  auto_trading_enabled?: boolean
  trading_mode?: 'paper' | 'live'
  created_at: string
  updated_at?: string
}

export interface ClientCreate {
  first_name: string
  last_name: string
  email: string
  phone?: string
  date_of_birth?: string
  risk_tolerance?: string
}

// ============================================
// Brokerage Types
// ============================================

export interface Brokerage {
  brokerage_id: number
  name: string
  brokerage_type: string
  is_active: boolean
  created_at: string
}

export interface BrokerageAccount {
  id: number
  client_id: number
  brokerage_id: number
  account_number: string
  account_hash: string
  account_type: string
  is_active: boolean
  notes?: string
  created_at: string
  updated_at?: string
}

// ============================================
// Schwab Types
// ============================================

export interface SchwabToken {
  id: number
  client_id: number
  brokerage_id: number
  access_token: string
  refresh_token: string
  token_type: string
  expires_at: string
  created_at: string
  updated_at?: string
}

export interface SchwabAuthStatus {
  client_id: number
  is_connected: boolean
  token_expires_at?: string
  needs_refresh: boolean
  authorize_url?: string
}

export interface SchwabAccount {
  accountNumber: string
  hashValue: string
  type: string
  status: string
  isDayTrader: boolean
  isClosingOnlyRestricted: boolean
}

export interface Position {
  symbol: string
  quantity: number
  averagePrice: number
  currentPrice: number
  marketValue: number
  profitLoss: number
  profitLossPercent: number
  longQuantity: number
  shortQuantity: number
  assetType: string
}

export interface Balances {
  account_value: number
  cash: number
  buying_power: number
  equity: number
  long_market_value: number
  short_market_value: number
}

export interface Portfolio {
  account: SchwabAccount
  positions: Position[]
  balances: Balances
}

export interface Quote {
  symbol: string
  lastPrice: number
  bidPrice: number
  askPrice: number
  highPrice: number
  lowPrice: number
  openPrice: number
  closePrice: number
  totalVolume: number
  mark: number
  quoteTime: number
  tradeTime: number
}

// ============================================
// Trading Types
// ============================================

export interface Trade {
  symbol: string
  action: "BUY" | "SELL"
  shares: number
  weight_change: number
  dollar_amount: number
  reasoning: string
}

export interface TradeSummary {
  num_trades: number
  total_turnover: number
  total_buy_value: number
  total_sell_value: number
  cash_required: number
}

export interface TradeRecommendation {
  id: number
  client_id: number
  account_id: number
  rl_portfolio_id: number
  rl_portfolio_name: string
  recommendation_type: string
  trades: Trade[]
  status: "pending" | "approved" | "rejected" | "executed" | "partially_executed" | "failed"
  total_trades: number
  total_buy_value: number
  total_sell_value: number
  expected_turnover: number
  notes?: string
  created_at: string
  approved_at?: string
  executed_at?: string
}

export interface GenerateRecommendationRequest {
  client_id: number
  account_hash: string
  portfolio_id: number
}

export interface GenerateRecommendationResponse {
  recommendation_id: number
  portfolio_id: number
  portfolio_name: string
  current_allocation: Record<string, number>
  target_allocation: Record<string, number>
  trades: Trade[]
  summary: TradeSummary
}

export interface ExecuteRecommendationRequest {
  account_hash: string
}

export interface ExecuteRecommendationResponse {
  recommendation_id: number
  total_trades: number
  successful: number
  failed: number
  results: TradeExecutionResult[]
}

export interface TradeExecutionResult {
  success: boolean
  trade_id: number
  order_id?: string
  symbol: string
  action: string
  shares: number
  estimated_price?: number
  status: string
  error?: string
}

export interface TradeExecution {
  id: number
  recommendation_id?: number
  client_id: number
  account_id: number
  symbol: string
  action: string
  shares: number
  price?: number
  order_type: string
  status: string
  order_id?: string
  error_message?: string
  executed_at?: string
  created_at: string
}

// ============================================
// Portfolio Assignment Types
// ============================================

export interface PortfolioAssignment {
  id: number
  client_id: number
  account_id: number
  rl_portfolio_id: number
  allocation_percent: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

// ============================================
// RL Portfolio Types
// ============================================

export interface RLPortfolio {
  id: number
  name: string
  description?: string
  strategy_type: string
  model_path?: string
  is_active: boolean
  created_at: string
}

// ============================================
// API Response Types
// ============================================

export interface ApiError {
  detail: string
  status?: number
}

export interface ApiResponse<T> {
  data?: T
  error?: ApiError
}

export interface ListResponse<T> {
  items: T[]
  count: number
  total?: number
}

// ============================================
// Dashboard Stats Types
// ============================================

export interface DashboardStats {
  total_clients: number
  active_clients: number
  total_accounts: number
  total_portfolio_value: number
  pending_recommendations: number
  executed_trades_today: number
}
