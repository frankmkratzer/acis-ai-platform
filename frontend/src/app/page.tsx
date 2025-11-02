'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Brain, TrendingUp, Activity } from 'lucide-react'
import api from '@/lib/api'
import ClientFormModal from '@/components/ClientFormModal'
import type { Client, TradeRecommendation } from '@/types'

interface AutonomousStatus {
  market_regime: {
    regime_label: string
    regime_confidence: number
  } | null
  active_strategy: string
  portfolio_value: number
  cash_balance: number
  num_positions: number
}

interface RebalanceEvent {
  rebalance_date: string
  strategy_selected: string
  market_regime: string
  post_rebalance_value: number
  pre_rebalance_value: number
  status: string
}

interface AggregatePortfolioStats {
  total_portfolio_value: number
  total_positions_value: number
  total_cash: number
  total_clients: number
  total_accounts: number
  total_positions: number
}

export default function DashboardPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [recommendations, setRecommendations] = useState<TradeRecommendation[]>([])
  const [autonomousStatus, setAutonomousStatus] = useState<AutonomousStatus | null>(null)
  const [lastRebalance, setLastRebalance] = useState<RebalanceEvent | null>(null)
  const [portfolioStats, setPortfolioStats] = useState<AggregatePortfolioStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showClientModal, setShowClientModal] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch clients and recommendations
      const [clientsData, recsData] = await Promise.all([
        api.clients.list(0, 10),
        api.trading.getRecommendations(undefined, 'pending', 5),
      ])

      setClients(clientsData)
      setRecommendations(recsData.recommendations)

      // Fetch aggregate portfolio stats
      try {
        const stats = await api.clients.getAggregatePortfolioStats()
        setPortfolioStats(stats)
      } catch (err) {
        console.error('Failed to fetch portfolio stats:', err)
      }

      // Fetch autonomous data separately with error handling
      try {
        const autonomousData = await api.autonomous.getStatus()
        setAutonomousStatus(autonomousData)
      } catch (err) {
        console.error('Failed to fetch autonomous status:', err)
      }

      try {
        const rebalancesData = await api.autonomous.getRebalances(1, 0)
        if (rebalancesData.length > 0) {
          setLastRebalance(rebalancesData[0])
        }
      } catch (err) {
        console.error('Failed to fetch rebalances:', err)
      }
    } catch (err: any) {
      console.error('Failed to fetch dashboard data:', err)
      setError(err.detail || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const handleClientModalSave = () => {
    fetchData()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800">Error Loading Dashboard</h3>
        <p className="mt-2 text-sm text-red-700">{error}</p>
      </div>
    )
  }

  const activeClients = clients.filter((c) => c.is_active).length
  const pendingRecommendations = recommendations.length

  const getRegimeBadgeColor = (regime: string) => {
    if (regime.includes('bull')) return 'bg-green-100 text-green-800'
    if (regime.includes('bear')) return 'bg-red-100 text-red-800'
    return 'bg-yellow-100 text-yellow-800'
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">
          Welcome to ACIS AI Platform - AI-Powered Wealth Management
        </p>
      </div>

      {/* Total Client Assets Card */}
      {portfolioStats && (
        <div
          className="bg-gradient-to-r from-green-600 to-teal-600 rounded-lg shadow-lg p-6 text-white"
          title="Aggregate portfolio metrics across all active clients including total assets under management, cash reserves, and invested positions"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Total Client Assets</h2>
                <p className="text-green-100">Assets under management across all clients</p>
              </div>
            </div>
            <Link
              href="/clients"
              title="View detailed client list and individual portfolio holdings"
              className="px-4 py-2 bg-white text-green-600 rounded-lg hover:bg-green-50 transition-colors font-medium"
            >
              View Clients →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-6">
            {/* Total Portfolio Value */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-green-100 text-sm mb-1">Portfolio Value</p>
              <p className="text-2xl font-bold">
                ${portfolioStats.total_portfolio_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-green-100 text-xs mt-1">
                total value
              </p>
            </div>

            {/* Cash Balance */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-green-100 text-sm mb-1">Cash</p>
              <p className="text-2xl font-bold">
                ${portfolioStats.total_cash.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-green-100 text-xs mt-1">
                {portfolioStats.total_portfolio_value > 0
                  ? ((portfolioStats.total_cash / portfolioStats.total_portfolio_value) * 100).toFixed(1)
                  : '0'}% cash
              </p>
            </div>

            {/* Positions Value */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-green-100 text-sm mb-1">Invested</p>
              <p className="text-2xl font-bold">
                ${portfolioStats.total_positions_value.toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-green-100 text-xs mt-1">
                {portfolioStats.total_positions} positions
              </p>
            </div>

            {/* Total Clients */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-green-100 text-sm mb-1">Active Clients</p>
              <p className="text-2xl font-bold">
                {portfolioStats.total_clients}
              </p>
              <p className="text-green-100 text-xs mt-1">
                {portfolioStats.total_accounts} accounts
              </p>
            </div>

            {/* Average Portfolio Size */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-green-100 text-sm mb-1">Avg per Client</p>
              <p className="text-2xl font-bold">
                ${portfolioStats.total_clients > 0
                  ? (portfolioStats.total_portfolio_value / portfolioStats.total_clients).toLocaleString('en-US', { maximumFractionDigits: 0 })
                  : '0'}
              </p>
              <p className="text-green-100 text-xs mt-1">
                portfolio size
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Autonomous Fund Status - Featured */}
      {autonomousStatus && (
        <div
          className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg p-6 text-white"
          title="Autonomous trading system that automatically selects strategies based on market regime and rebalances portfolios using ML/RL models"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                <Brain className="w-7 h-7" />
              </div>
              <div>
                <h2 className="text-2xl font-bold">Autonomous Trading Fund</h2>
                <p className="text-blue-100">AI-powered portfolio management</p>
              </div>
            </div>
            <Link
              href="/autonomous"
              title="View autonomous trading system dashboard with regime detection, strategy selection, and rebalancing history"
              className="px-4 py-2 bg-white text-blue-600 rounded-lg hover:bg-blue-50 transition-colors font-medium"
            >
              View Details →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
            {/* Portfolio Value */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-blue-100 text-sm mb-1">Portfolio Value</p>
              <p className="text-2xl font-bold">
                ${(autonomousStatus.portfolio_value || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-blue-100 text-xs mt-1">
                {autonomousStatus.num_positions} positions
              </p>
            </div>

            {/* Market Regime */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-blue-100 text-sm mb-1">Market Regime</p>
              {autonomousStatus.market_regime ? (
                <>
                  <p className="text-xl font-bold capitalize">
                    {autonomousStatus.market_regime.regime_label.replace(/_/g, ' ')}
                  </p>
                  <p className="text-blue-100 text-xs mt-1">
                    {(autonomousStatus.market_regime.regime_confidence * 100).toFixed(0)}% confidence
                  </p>
                </>
              ) : (
                <p className="text-lg">Analyzing...</p>
              )}
            </div>

            {/* Active Strategy */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-blue-100 text-sm mb-1">Active Strategy</p>
              <p className="text-xl font-bold capitalize">
                {autonomousStatus.active_strategy.replace(/_/g, ' ')}
              </p>
              <p className="text-blue-100 text-xs mt-1">ML + RL optimized</p>
            </div>

            {/* Last Rebalance */}
            <div className="bg-white/10 rounded-lg p-4 backdrop-blur-sm">
              <p className="text-blue-100 text-sm mb-1">Last Rebalance</p>
              {lastRebalance ? (
                <>
                  <p className="text-xl font-bold">
                    {new Date(lastRebalance.rebalance_date).toLocaleDateString()}
                  </p>
                  <p className="text-blue-100 text-xs mt-1">
                    {lastRebalance.status === 'completed' ? 'Completed' : lastRebalance.status}
                  </p>
                </>
              ) : (
                <p className="text-lg">No data</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Clients */}
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Total number of clients registered in the system including active and inactive accounts"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Clients</p>
              <p className="text-2xl font-bold text-gray-900">{clients.length}</p>
            </div>
          </div>
        </div>

        {/* Active Clients */}
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Number of clients with active accounts that can receive trade recommendations and execute trades"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Active Clients</p>
              <p className="text-2xl font-bold text-gray-900">{activeClients}</p>
            </div>
          </div>
        </div>

        {/* Pending Recommendations */}
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Trade recommendations awaiting approval. Review recommendations on the Trading page to approve or reject."
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-yellow-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Pending Recommendations</p>
              <p className="text-2xl font-bold text-gray-900">{pendingRecommendations}</p>
            </div>
          </div>
        </div>

        {/* API Status */}
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Backend API server connection status. All data and trading functionality requires the API to be online."
        >
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-purple-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
                  />
                </svg>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">API Status</p>
              <p className="text-2xl font-bold text-green-600">Online</p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Clients */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Clients</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {clients.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No clients found. Add your first client to get started.
              </div>
            ) : (
              clients.slice(0, 5).map((client) => (
                <Link
                  key={client.client_id}
                  href={`/clients/${client.client_id}`}
                  className="block px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {client.first_name} {client.last_name}
                      </p>
                      <p className="text-sm text-gray-500">{client.email}</p>
                    </div>
                    <div>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          client.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {client.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
          <div className="px-6 py-4 border-t border-gray-200">
            <Link
              href="/clients"
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              View all clients →
            </Link>
          </div>
        </div>

        {/* Pending Recommendations */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Pending Trade Recommendations
            </h2>
          </div>
          <div className="divide-y divide-gray-200">
            {recommendations.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No pending recommendations. Generate recommendations from the Trading page.
              </div>
            ) : (
              recommendations.map((rec) => (
                <Link
                  key={rec.id}
                  href={`/trading?recommendation=${rec.id}`}
                  className="block px-6 py-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {rec.rl_portfolio_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {rec.total_trades} trades • {(rec.expected_turnover * 100).toFixed(1)}%
                        turnover
                      </p>
                    </div>
                    <div>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        Pending
                      </span>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
          <div className="px-6 py-4 border-t border-gray-200">
            <Link
              href="/trading"
              className="text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              View all recommendations →
            </Link>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href="/autonomous"
            className="flex items-center p-4 border-2 border-blue-200 bg-blue-50 rounded-lg hover:bg-blue-100 hover:border-blue-300 transition-colors"
          >
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mr-4">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Autonomous Fund</p>
              <p className="text-xs text-gray-500">View AI trading system</p>
            </div>
          </Link>

          <button
            onClick={() => setShowClientModal(true)}
            title="Open form to add a new client with their brokerage accounts and investment preferences"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-blue-500 transition-colors text-left"
          >
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-4">
              <svg
                className="w-5 h-5 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Add Client</p>
              <p className="text-xs text-gray-500">Create new client account</p>
            </div>
          </button>

          <Link
            href="/trading"
            title="View trade recommendations across all clients and generate new ML/RL-optimized portfolio trades"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-blue-500 transition-colors"
          >
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mr-4">
              <svg
                className="w-5 h-5 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">Generate Recommendations</p>
              <p className="text-xs text-gray-500">Run RL models for trades</p>
            </div>
          </Link>

          <Link
            href="/trading/history"
            title="View all executed trades with their status, fill prices, and execution details"
            className="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-blue-500 transition-colors"
          >
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mr-4">
              <svg
                className="w-5 h-5 text-purple-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">View Trade History</p>
              <p className="text-xs text-gray-500">See executed trades</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Client Form Modal */}
      <ClientFormModal
        isOpen={showClientModal}
        onClose={() => setShowClientModal(false)}
        onSave={handleClientModalSave}
      />
    </div>
  )
}
