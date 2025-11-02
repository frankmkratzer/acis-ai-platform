'use client'

import React, { useState } from 'react'

interface BacktestConfig {
  start_date: string
  end_date: string
  initial_capital: number
  top_n: number
  weighting: string
  max_position: number
  rebalance_frequency: number
  transaction_cost: number
  min_market_cap: number
}

interface PerformanceMetrics {
  total_return: number
  annualized_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  final_capital: number
  total_periods: number
  total_transaction_costs: number
}

interface RebalanceEvent {
  date: string
  portfolio_value: number
  period_return: number
  transaction_costs: number
  num_positions: number
  predicted_return: number
  actual_return: number
}

interface BacktestResults {
  performance_metrics: PerformanceMetrics
  rebalance_history: RebalanceEvent[]
  config: any
}

export default function BacktestPage() {
  const [config, setConfig] = useState<BacktestConfig>({
    start_date: '2024-01-01',
    end_date: '2024-10-30',
    initial_capital: 100000,
    top_n: 50,
    weighting: 'signal',
    max_position: 0.10,
    rebalance_frequency: 20,
    transaction_cost: 0.001,
    min_market_cap: 2000000000  // $2B default (mid-cap+)
  })

  const [results, setResults] = useState<BacktestResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runBacktest = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('http://192.168.50.234:8000/api/backtest/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Backtest failed')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  const formatCurrency = (value: number) => {
    return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Autonomous System Backtesting</h1>
          <p className="text-gray-600 mt-2">
            Validate the autonomous trading system (ML + RL models) on historical data
          </p>
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>Note:</strong> This backtester validates the full autonomous system including market regime detection,
              meta-strategy selection, XGBoost stock selection, and PPO portfolio optimization. For detailed backtest results,
              see <code className="bg-blue-100 px-2 py-1 rounded">backtesting/results/</code> directory.
            </p>
          </div>
        </div>

        {/* Configuration Panel */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Backtest Configuration</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={config.start_date}
                onChange={(e) => setConfig({...config, start_date: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={config.end_date}
                onChange={(e) => setConfig({...config, end_date: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Initial Capital</label>
              <input
                type="number"
                value={config.initial_capital}
                onChange={(e) => setConfig({...config, initial_capital: parseFloat(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* Portfolio Settings */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Top N Stocks</label>
              <input
                type="number"
                value={config.top_n}
                onChange={(e) => setConfig({...config, top_n: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Weighting</label>
              <select
                value={config.weighting}
                onChange={(e) => setConfig({...config, weighting: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="equal">Equal Weight</option>
                <option value="rank">Rank Weight</option>
                <option value="signal">Signal Weight</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Position</label>
              <input
                type="number"
                step="0.01"
                value={config.max_position}
                onChange={(e) => setConfig({...config, max_position: parseFloat(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Market Cap Filter</label>
              <select
                value={config.min_market_cap}
                onChange={(e) => setConfig({...config, min_market_cap: parseFloat(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={0}>All Stocks</option>
                <option value={300000000}>Small+ (&gt;$300M)</option>
                <option value={2000000000}>Mid+ (&gt;$2B)</option>
                <option value={10000000000}>Large+ (&gt;$10B)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {/* Advanced Settings */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rebalance Frequency (days)
              </label>
              <input
                type="number"
                value={config.rebalance_frequency}
                onChange={(e) => setConfig({...config, rebalance_frequency: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Transaction Cost (bps)
              </label>
              <input
                type="number"
                step="0.1"
                value={config.transaction_cost * 10000}
                onChange={(e) => setConfig({...config, transaction_cost: parseFloat(e.target.value) / 10000})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <button
            onClick={runBacktest}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading ? 'Running Backtest...' : 'Run Backtest'}
          </button>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Results Panel */}
        {results && (
          <>
            {/* Performance Metrics */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Performance Metrics</h2>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Total Return</p>
                  <p className={`text-2xl font-bold ${results.performance_metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(results.performance_metrics.total_return)}
                  </p>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Annualized Return</p>
                  <p className={`text-2xl font-bold ${results.performance_metrics.annualized_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatPercent(results.performance_metrics.annualized_return)}
                  </p>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Sharpe Ratio</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {results.performance_metrics.sharpe_ratio.toFixed(2)}
                  </p>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Max Drawdown</p>
                  <p className="text-2xl font-bold text-red-600">
                    {formatPercent(results.performance_metrics.max_drawdown)}
                  </p>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Win Rate</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatPercent(results.performance_metrics.win_rate)}
                  </p>
                </div>

                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Final Capital</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatCurrency(results.performance_metrics.final_capital)}
                  </p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded">
                  <p className="text-sm text-gray-600">Total Rebalances</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {results.performance_metrics.total_periods}
                  </p>
                </div>

                <div className="bg-gray-50 p-3 rounded">
                  <p className="text-sm text-gray-600">Total Transaction Costs</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {formatCurrency(results.performance_metrics.total_transaction_costs)}
                  </p>
                </div>
              </div>
            </div>

            {/* Rebalance History */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Rebalance History</h2>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Portfolio Value
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Period Return
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Predicted Return
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actual Return
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Positions
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Txn Costs
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {results.rebalance_history.map((event, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {formatDate(event.date)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                          {formatCurrency(event.portfolio_value)}
                        </td>
                        <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${
                          event.period_return >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {formatPercent(event.period_return)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600">
                          {formatPercent(event.predicted_return)}
                        </td>
                        <td className={`px-4 py-3 whitespace-nowrap text-sm text-right ${
                          event.actual_return >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {formatPercent(event.actual_return)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">
                          {event.num_positions}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-600">
                          {formatCurrency(event.transaction_costs)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
