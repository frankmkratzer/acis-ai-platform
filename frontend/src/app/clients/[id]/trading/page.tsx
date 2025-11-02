'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import axios from 'axios'
import type { Client, TradeRecommendation, Trade, BrokerageAccount } from '@/types'

// Simple API client
const apiClient = axios.create({
  baseURL: 'http://192.168.50.234:8000',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  auth: { username: 'admin@acis-ai.com', password: 'admin123' },
})

export default function ClientTradingPage() {
  const params = useParams()
  const clientId = Number(params.id)

  const [client, setClient] = useState<Client | null>(null)
  const [clientAccounts, setClientAccounts] = useState<BrokerageAccount[]>([])
  const [selectedAccountHash, setSelectedAccountHash] = useState('')
  const [recommendations, setRecommendations] = useState<TradeRecommendation[]>([])
  const [selectedPortfolio, setSelectedPortfolio] = useState(1)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [selectedRecommendation, setSelectedRecommendation] = useState<TradeRecommendation | null>(
    null
  )
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    fetchData()
  }, [clientId])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [clientData, accountsData, recsData] = await Promise.all([
        api.clients.get(clientId),
        apiClient.get(`/api/brokerages/client/${clientId}/accounts`),
        api.trading.getRecommendations(clientId, undefined, 50),
      ])

      setClient(clientData)
      setClientAccounts(accountsData.data)
      setRecommendations(recsData.recommendations)

      // Auto-populate account hash with first active account
      if (accountsData.data.length > 0) {
        const activeAccount =
          accountsData.data.find((acc: BrokerageAccount) => acc.is_active) || accountsData.data[0]
        setSelectedAccountHash(activeAccount.account_hash)
      }
    } catch (err: any) {
      console.error('Failed to fetch data:', err)
      showMessage('error', err.detail || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }

  const handleGenerateRecommendations = async () => {
    if (!selectedAccountHash) {
      showMessage('error', 'Please select an account')
      return
    }

    try {
      setGenerating(true)
      await api.trading.generateRecommendations({
        client_id: clientId,
        account_hash: selectedAccountHash,
        portfolio_id: selectedPortfolio,
      })
      showMessage('success', 'Recommendations generated successfully!')
      await fetchData()
    } catch (err: any) {
      console.error('Failed to generate recommendations:', err)
      showMessage('error', err.detail || err.message || 'Failed to generate recommendations')
    } finally {
      setGenerating(false)
    }
  }

  const handleApprove = async (recommendationId: number) => {
    try {
      await api.trading.approveRecommendation(recommendationId)
      showMessage('success', 'Recommendation approved!')
      await fetchData()
    } catch (err: any) {
      showMessage('error', err.detail || err.message || 'Failed to approve')
    }
  }

  const handleReject = async (recommendationId: number) => {
    const reason = prompt('Enter reason for rejection:')
    if (!reason) return

    try {
      await api.trading.rejectRecommendation(recommendationId, reason)
      showMessage('success', 'Recommendation rejected')
      await fetchData()
    } catch (err: any) {
      showMessage('error', err.detail || err.message || 'Failed to reject')
    }
  }

  const handleExecute = async (recommendationId: number) => {
    if (!confirm('Are you sure you want to execute these trades? This will place real orders.')) {
      return
    }

    if (!selectedAccountHash) {
      showMessage('error', 'No account hash selected')
      return
    }

    try {
      const result = await api.trading.executeRecommendation(recommendationId, {
        account_hash: selectedAccountHash,
      })
      showMessage(
        'success',
        `Execution complete! Successful: ${result.successful}, Failed: ${result.failed}`
      )
      await fetchData()
    } catch (err: any) {
      showMessage('error', err.detail || err.message || 'Failed to execute')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading trading data...</p>
        </div>
      </div>
    )
  }

  if (!client) {
    return (
      <div className="p-8">
        <div className="text-center">
          <p className="text-red-600">Client not found</p>
          <Link href="/clients" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
            ← Back to Clients
          </Link>
        </div>
      </div>
    )
  }

  const portfolios = [
    { id: 1, name: 'Growth/Momentum', description: 'High growth + momentum stocks' },
    { id: 2, name: 'Dividend', description: 'High dividend yield stocks' },
    { id: 3, name: 'Value', description: 'Undervalued quality stocks' },
  ]

  const pendingRecs = recommendations.filter((r) => r.status === 'pending')
  const approvedRecs = recommendations.filter((r) => r.status === 'approved')

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link href="/clients" className="text-blue-600 hover:text-blue-700">
            ← Back to Clients
          </Link>
          <span className="mx-2 text-gray-400">/</span>
          <Link
            href={`/clients/${clientId}`}
            className="text-blue-600 hover:text-blue-700"
          >
            {client.first_name} {client.last_name}
          </Link>
        </div>

        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Trading - {client.first_name} {client.last_name}
          </h1>
          <p className="mt-2 text-gray-600">
            Generate AI-powered trade recommendations and execute orders
          </p>
        </div>

        {/* Message Alert */}
        {message && (
          <div
            className={`p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Generate Recommendations */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Generate New Recommendations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Brokerage Account
              </label>
              {clientAccounts.length === 0 ? (
                <div className="text-sm text-gray-500">
                  No brokerage accounts found. Please connect a brokerage account first.
                </div>
              ) : (
                <select
                  value={selectedAccountHash}
                  onChange={(e) => setSelectedAccountHash(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {clientAccounts.map((account) => (
                    <option key={account.id} value={account.account_hash}>
                      {account.account_number} ({account.account_type})
                      {account.is_active ? '' : ' - Inactive'}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Portfolio</label>
              <select
                value={selectedPortfolio}
                onChange={(e) => setSelectedPortfolio(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {portfolios.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={handleGenerateRecommendations}
                disabled={generating || clientAccounts.length === 0}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {generating ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
          <p className="mt-4 text-sm text-gray-500">
            Selected portfolio:{' '}
            <span className="font-medium">
              {portfolios.find((p) => p.id === selectedPortfolio)?.description}
            </span>
          </p>
        </div>

        {/* Pending Recommendations */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Pending Recommendations ({pendingRecs.length})
            </h2>
          </div>
          {pendingRecs.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No pending recommendations. Generate recommendations above.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {pendingRecs.map((rec) => (
                <div key={rec.id} className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">
                        {rec.rl_portfolio_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {rec.total_trades} trades • {(rec.expected_turnover * 100).toFixed(1)}%
                        turnover • Created {new Date(rec.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() =>
                          setSelectedRecommendation(
                            selectedRecommendation?.id === rec.id ? null : rec
                          )
                        }
                        className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                      >
                        {selectedRecommendation?.id === rec.id ? 'Hide' : 'View'} Details
                      </button>
                      <button
                        onClick={() => handleApprove(rec.id)}
                        className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(rec.id)}
                        className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                      >
                        Reject
                      </button>
                    </div>
                  </div>

                  {/* Trade Details */}
                  {selectedRecommendation?.id === rec.id && (
                    <div className="mt-4 border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Trades:</h4>
                      <div className="space-y-2">
                        {rec.trades.map((trade: Trade, idx: number) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                          >
                            <div className="flex items-center space-x-4">
                              <span
                                className={`px-2.5 py-1 rounded text-xs font-medium ${
                                  trade.action === 'BUY'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}
                              >
                                {trade.action}
                              </span>
                              <span className="font-medium text-gray-900">{trade.symbol}</span>
                              <span className="text-sm text-gray-600">{trade.shares} shares</span>
                              <span className="text-sm text-gray-600">
                                ${trade.dollar_amount.toLocaleString()}
                              </span>
                            </div>
                            <div className="text-sm text-gray-500 max-w-md">{trade.reasoning}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Approved Recommendations */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Approved Recommendations ({approvedRecs.length})
            </h2>
          </div>
          {approvedRecs.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No approved recommendations ready to execute.
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {approvedRecs.map((rec) => (
                <div key={rec.id} className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">
                        {rec.rl_portfolio_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {rec.total_trades} trades • Approved{' '}
                        {new Date(rec.approved_at || '').toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => handleExecute(rec.id)}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                    >
                      Execute Trades
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recommendation History */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">All Recommendations</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Portfolio
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Trades
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Turnover
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {recommendations.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      No recommendations yet. Generate your first recommendation above.
                    </td>
                  </tr>
                ) : (
                  recommendations.map((rec) => (
                    <tr key={rec.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {rec.rl_portfolio_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {rec.total_trades}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {(rec.expected_turnover * 100).toFixed(1)}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            rec.status === 'pending'
                              ? 'bg-yellow-100 text-yellow-800'
                              : rec.status === 'approved'
                              ? 'bg-green-100 text-green-800'
                              : rec.status === 'executed'
                              ? 'bg-blue-100 text-blue-800'
                              : rec.status === 'rejected'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {rec.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(rec.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
