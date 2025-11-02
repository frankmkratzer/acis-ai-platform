'use client'

import { useEffect, useState } from 'react'
import { Activity, TrendingUp, Brain, Zap, AlertTriangle, CheckCircle, Clock, Play } from 'lucide-react'
import api from '@/lib/api'
import Tooltip from '@/components/Tooltip'

interface MarketRegime {
  date: string
  regime_label: string
  regime_confidence: number
  volatility_regime: string
  trend_regime: string
  realized_volatility_20d: number
}

interface AutonomousStatus {
  market_regime: MarketRegime | null
  active_strategy: string
  strategy_confidence: number
  portfolio_value: number
  cash_balance: number
  num_positions: number
  max_drift: number
  max_drift_ticker: string
  next_rebalance: string
  ml_model_status: string
  rl_model_status: string
  risk_status: string
  paper_trading: boolean
}

interface RebalanceEvent {
  id: number
  rebalance_date: string
  strategy_selected: string
  market_regime: string
  num_buys: number
  num_sells: number
  post_rebalance_value: number
  pre_rebalance_value: number
  status: string
}

export default function AutonomousPage() {
  const [status, setStatus] = useState<AutonomousStatus | null>(null)
  const [recentRebalances, setRecentRebalances] = useState<RebalanceEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rebalancing, setRebalancing] = useState(false)
  const [rebalanceSuccess, setRebalanceSuccess] = useState(false)
  const [rebalanceMessage, setRebalanceMessage] = useState<string | null>(null)

  useEffect(() => {
    fetchData()
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [statusData, rebalancesData] = await Promise.all([
        api.autonomous.getStatus(),
        api.autonomous.getRebalances(10, 0)
      ])

      setStatus(statusData)
      setRecentRebalances(rebalancesData)
    } catch (err: any) {
      console.error('Error fetching autonomous data:', err)
      setError(err.detail || err.message || 'Failed to fetch autonomous data')
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerRebalance = async (dryRun: boolean = true) => {
    try {
      setRebalancing(true)
      setError(null)
      setRebalanceSuccess(false)
      setRebalanceMessage(null)

      const result = await api.autonomous.triggerRebalance(false, dryRun)
      setRebalanceSuccess(true)
      setRebalanceMessage(result.message || `Rebalance ${dryRun ? 'dry run' : ''} completed successfully`)

      // Auto-refresh data after rebalance
      setTimeout(() => {
        setRebalanceSuccess(false)
        setRebalanceMessage(null)
        fetchData()
      }, 3000)
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to trigger rebalance')
    } finally {
      setRebalancing(false)
    }
  }

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading autonomous system status...</p>
        </div>
      </div>
    )
  }

  if (error && !status) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-semibold">Error</h3>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    )
  }

  const getRegimeBadgeColor = (regime: string) => {
    if (regime.includes('bull')) return 'bg-green-100 text-green-800'
    if (regime.includes('bear')) return 'bg-red-100 text-red-800'
    return 'bg-yellow-100 text-yellow-800'
  }

  const getStatusIcon = (status: string) => {
    if (status === 'active' || status === 'operational') return <CheckCircle className="w-5 h-5 text-green-600" />
    if (status === 'training' || status === 'fallback') return <Clock className="w-5 h-5 text-yellow-600" />
    return <AlertTriangle className="w-5 h-5 text-red-600" />
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="w-8 h-8 text-blue-600" />
            Autonomous Trading System
          </h1>
          <p className="text-gray-600 mt-1">
            AI-powered portfolio management with real-time market adaptation
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            {status?.paper_trading ? (
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                Paper Trading
              </span>
            ) : (
              <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium">
                LIVE TRADING
              </span>
            )}
            <div className="absolute -right-6 top-1/2 -translate-y-1/2">
              <Tooltip content={status?.paper_trading ? "Paper trading mode - all trades are simulated, no real money at risk." : "LIVE TRADING - Real money is being used. All trades execute in your brokerage account."} />
            </div>
          </div>
          <div className="relative">
            <button
              onClick={() => handleTriggerRebalance(true)}
              disabled={rebalancing}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              <Play className={`w-4 h-4 ${rebalancing ? 'animate-pulse' : ''}`} />
              {rebalancing ? 'Rebalancing...' : 'Trigger Rebalance'}
            </button>
            <div className="absolute -right-6 top-1/2 -translate-y-1/2">
              <Tooltip
                content="Manually trigger a portfolio rebalance. The system analyzes market conditions, selects optimal strategy, and generates trade recommendations."
                learnMoreLink="/docs/autonomous#rebalancing"
              />
            </div>
          </div>
          <div className="relative">
            <button
              onClick={fetchData}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Refresh
            </button>
            <div className="absolute -right-6 top-1/2 -translate-y-1/2">
              <Tooltip content="Refresh autonomous system status. Data auto-refreshes every 30 seconds." />
            </div>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {rebalanceSuccess && rebalanceMessage && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
          <CheckCircle className="w-5 h-5 inline mr-2" />
          {rebalanceMessage}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <AlertTriangle className="w-5 h-5 inline mr-2" />
          {error}
        </div>
      )}

      {/* Top Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Market Regime */}
        <div className="bg-white rounded-lg shadow-md p-6 relative group">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Market Regime</h3>
            <Activity className="w-6 h-6 text-blue-600" />
          </div>
          <div className="absolute top-2 right-2">
            <Tooltip
              content="Current market regime detected by AI. The system adapts strategy based on market conditions (bull/bear) and volatility levels."
              learnMoreLink="/docs/autonomous#market-regime"
            />
          </div>
          {status?.market_regime ? (
            <div className="space-y-2">
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getRegimeBadgeColor(status.market_regime.regime_label)}`}>
                {status.market_regime.regime_label.replace(/_/g, ' ').toUpperCase()}
              </span>
              <div className="mt-3">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Confidence</span>
                  <span className="font-semibold">{(status.market_regime.regime_confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: `${status.market_regime.regime_confidence * 100}%` }}
                  />
                </div>
              </div>
              <div className="mt-3 space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Trend:</span>
                  <span className="font-medium">{status.market_regime.trend_regime}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Volatility:</span>
                  <span className="font-medium">{status.market_regime.volatility_regime}</span>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">No regime data available</p>
          )}
        </div>

        {/* Active Strategy */}
        <div className="bg-white rounded-lg shadow-md p-6 relative group">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Active Strategy</h3>
            <TrendingUp className="w-6 h-6 text-green-600" />
          </div>
          <div className="absolute top-2 right-2">
            <Tooltip
              content="Currently active investment strategy selected by AI based on market regime. Each strategy targets specific stock characteristics (growth, value, dividend, etc.)."
              learnMoreLink="/docs/autonomous#strategies"
            />
          </div>
          <div className="space-y-2">
            <div className="text-2xl font-bold text-gray-900">
              {status?.active_strategy?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'N/A'}
            </div>
            <div className="mt-3">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Strategy Confidence</span>
                <span className="font-semibold">{((status?.strategy_confidence || 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{ width: `${(status?.strategy_confidence || 0) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Next Rebalance */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Next Rebalance</h3>
            <Clock className="w-6 h-6 text-purple-600" />
          </div>
          <div className="space-y-2">
            <div className="text-2xl font-bold text-gray-900">
              {status?.next_rebalance || 'Not scheduled'}
            </div>
            <p className="text-sm text-gray-600">
              Daily at 4:30 PM ET
            </p>
          </div>
        </div>
      </div>

      {/* Portfolio Status */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-gray-600">Current Value</p>
            <p className="text-2xl font-bold text-gray-900">
              ${(status?.portfolio_value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Cash</p>
            <p className="text-2xl font-bold text-gray-900">
              ${(status?.cash_balance || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
              <span className="text-sm text-gray-600 ml-2">
                ({((status?.cash_balance || 0) / (status?.portfolio_value || 1) * 100).toFixed(1)}%)
              </span>
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Positions</p>
            <p className="text-2xl font-bold text-gray-900">{status?.num_positions || 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Max Drift</p>
            <p className="text-2xl font-bold text-gray-900">
              {((status?.max_drift || 0) * 100).toFixed(1)}%
              {status?.max_drift_ticker && (
                <span className="text-sm text-gray-600 ml-2">({status.max_drift_ticker})</span>
              )}
            </p>
          </div>
        </div>

        {/* Risk Status */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2">
            {status?.risk_status === 'operational' ? (
              <>
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span className="text-green-700 font-medium">All risk checks passing</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-5 h-5 text-yellow-600" />
                <span className="text-yellow-700 font-medium">Risk limits exceeded</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Model Status */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-600" />
          Model Status
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-600">ML (XGBoost)</p>
              <p className="text-sm font-medium text-gray-900">Stock Selection</p>
            </div>
            {getStatusIcon(status?.ml_model_status || 'unknown')}
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-600">RL (PPO)</p>
              <p className="text-sm font-medium text-gray-900">Weight Optimization</p>
            </div>
            {getStatusIcon(status?.rl_model_status || 'unknown')}
          </div>
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm text-gray-600">Risk Manager</p>
              <p className="text-sm font-medium text-gray-900">Safety Controls</p>
            </div>
            {getStatusIcon(status?.risk_status || 'unknown')}
          </div>
        </div>
      </div>

      {/* Recent Rebalancing Events */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Rebalancing Events</h3>
        {recentRebalances.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Regime
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Strategy
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Trades
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P&L
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {recentRebalances.map((rebalance) => {
                  const pnl = rebalance.post_rebalance_value - rebalance.pre_rebalance_value
                  const pnlPercent = (pnl / rebalance.pre_rebalance_value) * 100
                  return (
                    <tr key={rebalance.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(rebalance.rebalance_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${getRegimeBadgeColor(rebalance.market_regime)}`}>
                          {rebalance.market_regime}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {rebalance.strategy_selected.replace(/_/g, ' ')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className="text-green-600">+{rebalance.num_buys}</span> /{' '}
                        <span className="text-red-600">-{rebalance.num_sells}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {pnl >= 0 ? '+' : ''}${pnl.toFixed(0)} ({pnlPercent.toFixed(2)}%)
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          rebalance.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {rebalance.status}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No rebalancing events yet</p>
        )}
      </div>
    </div>
  )
}
