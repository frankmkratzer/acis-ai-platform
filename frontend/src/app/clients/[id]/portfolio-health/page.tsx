'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import {
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  DollarSign,
  BarChart3,
  ArrowRightLeft,
  Download,
} from 'lucide-react'
import api from '@/lib/api'

interface PortfolioAnalysis {
  client_id: number
  account_id: string
  analysis_date: string
  positions: Position[]
  drift_analysis: DriftAnalysis
  underperformers: Underperformer[]
  swap_recommendations: SwapRecommendation[]
  tax_harvest_opportunities: TaxHarvestOpportunity[]
  health_score: number
  needs_rebalance: boolean
  total_portfolio_value: number
}

interface Position {
  ticker: string
  quantity: number
  current_price: number
  market_value: number
  current_weight: number
  target_weight: number
  cost_basis: number
  unrealized_gain_loss: number
  days_held: number
  sector: string
}

interface DriftAnalysis {
  positions: DriftPosition[]
  max_drift: number
  avg_drift: number
  positions_exceeding_threshold: number
}

interface DriftPosition {
  ticker: string
  current_weight: number
  target_weight: number
  drift: number
  exceeds_threshold: boolean
}

interface Underperformer {
  ticker: string
  ml_score: number
  unrealized_pnl_pct: number
  current_weight: number
  reason: string
}

interface SwapRecommendation {
  sell_ticker: string
  buy_ticker: string
  reason: string
  expected_improvement: number
  sell_ml_score: number
  buy_ml_score: number
  tax_impact: number
  transaction_cost: number
  net_benefit: number
  priority: 'high' | 'medium' | 'low'
}

interface TaxHarvestOpportunity {
  ticker: string
  unrealized_loss: number
  tax_benefit: number
  market_value: number
  recommendation: string
}

export default function PortfolioHealthPage() {
  const params = useParams()
  const clientId = parseInt(params.id as string)

  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncSuccess, setSyncSuccess] = useState(false)
  const [minPriority, setMinPriority] = useState<'low' | 'medium' | 'high'>('low')

  useEffect(() => {
    fetchAnalysis()
  }, [clientId])

  const fetchAnalysis = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.portfolioHealth.getAnalysis(clientId)
      setAnalysis(data)
    } catch (err: any) {
      setError(err.detail || 'Failed to load portfolio analysis')
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchAnalysis()
    setRefreshing(false)
  }

  const handleSyncPositions = async () => {
    try {
      setSyncing(true)
      setError(null)
      setSyncSuccess(false)

      // Get client's account hash from their brokerage accounts
      const accounts = await api.brokerages.getClientAccounts(clientId)
      if (accounts.length === 0) {
        throw new Error('No brokerage accounts found for this client')
      }

      const accountHash = accounts[0].account_hash
      if (!accountHash) {
        throw new Error('Account hash not found')
      }

      // Sync positions
      await api.portfolioHealth.syncSchwabPositions(clientId, accountHash)
      setSyncSuccess(true)

      // Auto-refresh analysis after sync
      setTimeout(() => {
        setSyncSuccess(false)
        fetchAnalysis()
      }, 2000)
    } catch (err: any) {
      setError(err.detail || err.message || 'Failed to sync positions')
    } finally {
      setSyncing(false)
    }
  }

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getHealthBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-100'
    if (score >= 60) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-700 border-red-300'
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-300'
      case 'low':
        return 'bg-blue-100 text-blue-700 border-blue-300'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300'
    }
  }

  const filteredRecommendations = analysis?.swap_recommendations.filter((rec) => {
    if (minPriority === 'high') return rec.priority === 'high'
    if (minPriority === 'medium') return rec.priority === 'high' || rec.priority === 'medium'
    return true
  })

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <AlertTriangle className="w-5 h-5 inline mr-2" />
          {error}
        </div>
      </div>
    )
  }

  if (!analysis) return null

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Portfolio Health Analysis</h1>
          <p className="text-sm text-gray-500 mt-1">
            Last updated: {new Date(analysis.analysis_date).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSyncPositions}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            <Download className={`w-4 h-4 ${syncing ? 'animate-bounce' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync Schwab Positions'}
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Analysis'}
          </button>
        </div>
      </div>

      {/* Success Message */}
      {syncSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
          <CheckCircle className="w-5 h-5 inline mr-2" />
          Positions synced successfully! Refreshing analysis...
        </div>
      )}

      {/* Health Score Card */}
      <div className={`${getHealthBgColor(analysis.health_score)} rounded-lg p-6 border-2 ${analysis.needs_rebalance ? 'border-yellow-400' : 'border-green-400'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative w-32 h-32">
              {/* SVG Gauge */}
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
                <circle
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="12"
                />
                <circle
                  cx="60"
                  cy="60"
                  r="54"
                  fill="none"
                  stroke={analysis.health_score >= 80 ? '#10b981' : analysis.health_score >= 60 ? '#f59e0b' : '#ef4444'}
                  strokeWidth="12"
                  strokeDasharray={`${(analysis.health_score / 100) * 339.292} 339.292`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className={`text-3xl font-bold ${getHealthColor(analysis.health_score)}`}>
                    {analysis.health_score.toFixed(0)}
                  </div>
                  <div className="text-xs text-gray-600">Health</div>
                </div>
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {analysis.health_score >= 80 ? 'Excellent Health' : analysis.health_score >= 60 ? 'Good Health' : 'Needs Attention'}
              </h2>
              <p className="text-gray-700 mt-1">
                Portfolio Value: ${analysis.total_portfolio_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
              <div className="flex items-center gap-2 mt-2">
                {analysis.needs_rebalance ? (
                  <>
                    <AlertTriangle className="w-4 h-4 text-yellow-600" />
                    <span className="text-sm font-medium text-yellow-700">Rebalancing Recommended</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-sm font-medium text-green-700">Well Balanced</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{analysis.positions.length}</div>
              <div className="text-xs text-gray-600">Positions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{analysis.underperformers.length}</div>
              <div className="text-xs text-gray-600">Underperformers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{analysis.swap_recommendations.length}</div>
              <div className="text-xs text-gray-600">Recommendations</div>
            </div>
          </div>
        </div>
      </div>

      {/* Drift Analysis */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Position Drift Analysis</h3>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Max Drift</div>
            <div className="text-2xl font-bold text-gray-900">{(analysis.drift_analysis.max_drift * 100).toFixed(1)}%</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Avg Drift</div>
            <div className="text-2xl font-bold text-gray-900">{(analysis.drift_analysis.avg_drift * 100).toFixed(1)}%</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-600">Over Threshold</div>
            <div className="text-2xl font-bold text-gray-900">{analysis.drift_analysis.positions_exceeding_threshold}</div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-4 text-sm font-medium text-gray-700">Ticker</th>
                <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Current Weight</th>
                <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Target Weight</th>
                <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Drift</th>
                <th className="text-center py-2 px-4 text-sm font-medium text-gray-700">Status</th>
              </tr>
            </thead>
            <tbody>
              {analysis.drift_analysis.positions.map((drift, idx) => (
                <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 px-4 font-medium text-gray-900">{drift.ticker}</td>
                  <td className="py-2 px-4 text-right text-gray-700">{(drift.current_weight * 100).toFixed(2)}%</td>
                  <td className="py-2 px-4 text-right text-gray-700">{(drift.target_weight * 100).toFixed(2)}%</td>
                  <td className="py-2 px-4 text-right">
                    <span className={drift.exceeds_threshold ? 'text-red-600 font-semibold' : 'text-gray-700'}>
                      {(drift.drift * 100).toFixed(2)}%
                    </span>
                  </td>
                  <td className="py-2 px-4 text-center">
                    {drift.exceeds_threshold ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 text-red-700 rounded text-xs">
                        <AlertTriangle className="w-3 h-3" />
                        Over Threshold
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                        <CheckCircle className="w-3 h-3" />
                        OK
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Swap Recommendations */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">Swap Recommendations</h3>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Min Priority:</label>
            <select
              value={minPriority}
              onChange={(e) => setMinPriority(e.target.value as any)}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
        {filteredRecommendations && filteredRecommendations.length > 0 ? (
          <div className="space-y-4">
            {filteredRecommendations.map((rec, idx) => (
              <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getPriorityColor(rec.priority)}`}>
                        {rec.priority.toUpperCase()}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-red-600">{rec.sell_ticker}</span>
                        <ArrowRightLeft className="w-4 h-4 text-gray-400" />
                        <span className="font-semibold text-green-600">{rec.buy_ticker}</span>
                      </div>
                    </div>
                    <p className="text-sm text-gray-700 mb-3">{rec.reason}</p>
                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <div className="text-xs text-gray-500">Sell ML Score</div>
                        <div className="text-sm font-medium text-gray-900">{rec.sell_ml_score.toFixed(3)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500">Buy ML Score</div>
                        <div className="text-sm font-medium text-gray-900">{rec.buy_ml_score.toFixed(3)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500">Expected Improvement</div>
                        <div className="text-sm font-medium text-green-600">+{(rec.expected_improvement * 100).toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500">Net Benefit</div>
                        <div className="text-sm font-medium text-green-600">+{(rec.net_benefit * 100).toFixed(1)}%</div>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 ml-4">
                    <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm">
                      Approve
                    </button>
                    <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm">
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-2 text-gray-400" />
            <p>No swap recommendations at this priority level</p>
          </div>
        )}
      </div>

      {/* Tax-Loss Harvesting Opportunities */}
      {analysis.tax_harvest_opportunities.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold text-gray-900">Tax-Loss Harvesting Opportunities</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-4 text-sm font-medium text-gray-700">Ticker</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Unrealized Loss</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Tax Benefit</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Market Value</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-gray-700">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {analysis.tax_harvest_opportunities.map((opp, idx) => (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-4 font-medium text-gray-900">{opp.ticker}</td>
                    <td className="py-2 px-4 text-right text-red-600">
                      ${Math.abs(opp.unrealized_loss).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-4 text-right text-green-600 font-semibold">
                      ${opp.tax_benefit.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-4 text-right text-gray-700">
                      ${opp.market_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-4 text-sm text-gray-700">{opp.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 p-4 bg-green-50 rounded-lg">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              <span className="font-semibold text-green-900">
                Total Potential Tax Savings: $
                {analysis.tax_harvest_opportunities
                  .reduce((sum, opp) => sum + opp.tax_benefit, 0)
                  .toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Underperformers */}
      {analysis.underperformers.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-5 h-5 text-red-600" />
            <h3 className="text-lg font-semibold text-gray-900">Underperforming Positions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-4 text-sm font-medium text-gray-700">Ticker</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Market Value</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Unrealized Loss</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Loss %</th>
                  <th className="text-right py-2 px-4 text-sm font-medium text-gray-700">Weight</th>
                  <th className="text-left py-2 px-4 text-sm font-medium text-gray-700">Reason</th>
                </tr>
              </thead>
              <tbody>
                {analysis.underperformers.map((under, idx) => (
                  <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-2 px-4 font-medium text-gray-900">{under.ticker}</td>
                    <td className="py-2 px-4 text-right text-gray-700">
                      ${under.market_value?.toFixed(2) || '0.00'}
                    </td>
                    <td className="py-2 px-4 text-right">
                      <span className="text-red-600">
                        ${under.unrealized_loss?.toFixed(2) || '0.00'}
                      </span>
                    </td>
                    <td className="py-2 px-4 text-right">
                      <span className={under.unrealized_pnl_pct < 0 ? 'text-red-600 font-semibold' : 'text-green-600'}>
                        {(under.unrealized_pnl_pct * 100).toFixed(2)}%
                      </span>
                    </td>
                    <td className="py-2 px-4 text-right text-gray-700">{(under.current_weight * 100).toFixed(2)}%</td>
                    <td className="py-2 px-4 text-sm text-gray-700">{under.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
