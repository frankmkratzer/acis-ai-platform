'use client'

import { useState, useEffect } from 'react'

interface Trade {
  symbol: string
  action: string
  quantity: number
  current_quantity: number
  target_quantity: number
  estimated_value: number
  estimated_price?: number
  reason: string
}

interface OrderBatch {
  batch_id: string
  client_id: number
  account_hash: string
  portfolio_id: number
  strategy_name: string
  status: string
  created_at: string
  current_portfolio: any
  target_allocation: any[]
  trades: Trade[]
  trade_count: number
  estimated_total_value: number
}

export default function RLTradingPage() {
  const [batches, setBatches] = useState<OrderBatch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<OrderBatch | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [executing, setExecuting] = useState(false)

  // Form state for generating new rebalance
  const [clientId, setClientId] = useState(2) // Default to Heidi
  const [portfolioId, setPortfolioId] = useState(1) // Default to Growth/Momentum
  const [accountHash, setAccountHash] = useState('5A7016096116270530B605F06545A0F0DBB47036F4C7BA9D6758ABD9118F40DA')

  useEffect(() => {
    fetchBatches()
  }, [])

  const fetchBatches = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/rl/trading/batches?limit=50')
      const data = await response.json()
      setBatches(data.batches || [])
    } catch (error) {
      console.error('Failed to fetch batches:', error)
    } finally {
      setLoading(false)
    }
  }

  const generateRebalance = async () => {
    setGenerating(true)
    try {
      const response = await fetch('http://localhost:8000/api/rl/trading/rebalance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          account_hash: accountHash,
          portfolio_id: portfolioId,
          max_positions: 10,
          require_approval: true
        })
      })

      if (!response.ok) {
        const error = await response.json()
        alert(`Failed to generate rebalance: ${error.detail}`)
        return
      }

      const batch = await response.json()
      setSelectedBatch(batch)
      fetchBatches() // Refresh list
    } catch (error) {
      console.error('Failed to generate rebalance:', error)
      alert('Failed to generate rebalance')
    } finally {
      setGenerating(false)
    }
  }

  const approveBatch = async (batchId: string, dryRun: boolean = true) => {
    if (!confirm(`Are you sure you want to ${dryRun ? 'DRY RUN' : 'EXECUTE LIVE'} this order batch?`)) {
      return
    }

    setExecuting(true)
    try {
      const response = await fetch(`http://localhost:8000/api/rl/trading/batches/${batchId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          execute_immediately: true,
          dry_run: dryRun
        })
      })

      const result = await response.json()

      if (result.success) {
        alert(`Batch ${dryRun ? 'validated successfully' : 'executed!'}`)
        fetchBatches()
        if (selectedBatch?.batch_id === batchId) {
          setSelectedBatch(null)
        }
      } else {
        alert(`Failed: ${result.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Failed to approve batch:', error)
      alert('Failed to approve batch')
    } finally {
      setExecuting(false)
    }
  }

  const rejectBatch = async (batchId: string) => {
    if (!confirm('Are you sure you want to reject this order batch?')) {
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/api/rl/trading/batches/${batchId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'User rejected' })
      })

      const result = await response.json()
      if (result.success) {
        alert('Batch rejected')
        fetchBatches()
        if (selectedBatch?.batch_id === batchId) {
          setSelectedBatch(null)
        }
      }
    } catch (error) {
      console.error('Failed to reject batch:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending_approval':
        return 'bg-yellow-100 text-yellow-800'
      case 'approved':
        return 'bg-blue-100 text-blue-800'
      case 'executed':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      case 'dry_run_validated':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading RL trading data...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">RL-Powered Live Trading</h1>
          <p className="text-gray-600 mt-2">AI-generated rebalancing recommendations with approval workflow</p>
        </div>

        {/* Generate New Rebalance */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Generate New Rebalance</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Client</label>
              <select
                value={clientId}
                onChange={(e) => setClientId(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              >
                <option value={1}>Frank Kratzer (Client 1)</option>
                <option value={2}>Heidi Abele (Client 2)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Strategy</label>
              <select
                value={portfolioId}
                onChange={(e) => setPortfolioId(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
              >
                <option value={1}>Growth / Momentum</option>
                <option value={2}>Dividend</option>
                <option value={3}>Value</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={generateRebalance}
                disabled={generating}
                className="w-full px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
              >
                {generating ? 'Generating...' : 'Generate Rebalance'}
              </button>
            </div>
          </div>

          <p className="text-sm text-gray-500">
            This will use the trained RL model to analyze the current portfolio and generate optimal rebalancing trades.
            All trades require approval before execution.
          </p>
        </div>

        {/* Selected Batch Detail */}
        {selectedBatch && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{selectedBatch.strategy_name}</h2>
                <p className="text-sm text-gray-500">Batch ID: {selectedBatch.batch_id}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedBatch.status)}`}>
                {selectedBatch.status}
              </span>
            </div>

            {/* Portfolio Summary */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Current Value</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${selectedBatch.current_portfolio?.total_value?.toLocaleString() || 'N/A'}
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Cash Available</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${selectedBatch.current_portfolio?.cash_available?.toLocaleString() || 'N/A'}
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-sm text-gray-600">Total Trades</p>
                <p className="text-2xl font-bold text-gray-900">{selectedBatch.trade_count}</p>
              </div>
            </div>

            {/* Trades Table */}
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Proposed Trades</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estimated Value</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Reason</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {selectedBatch.trades.map((trade, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900">{trade.symbol}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${trade.action === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {trade.action}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                        {trade.quantity} shares
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                        ${trade.estimated_value.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">{trade.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Action Buttons */}
            {selectedBatch.status === 'pending_approval' && (
              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => approveBatch(selectedBatch.batch_id, true)}
                  disabled={executing}
                  className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400"
                >
                  Dry Run (Validate Only)
                </button>
                <button
                  onClick={() => approveBatch(selectedBatch.batch_id, false)}
                  disabled={executing}
                  className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400"
                >
                  Execute Live Trades
                </button>
                <button
                  onClick={() => rejectBatch(selectedBatch.batch_id)}
                  disabled={executing}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400"
                >
                  Reject
                </button>
              </div>
            )}
          </div>
        )}

        {/* Batch History */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Rebalance History</h2>

          {batches.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No rebalance orders yet. Generate one above to get started.</p>
          ) : (
            <div className="space-y-3">
              {batches.map((batch) => (
                <div
                  key={batch.batch_id}
                  onClick={() => setSelectedBatch(batch)}
                  className="border border-gray-200 rounded-lg p-4 hover:border-blue-500 cursor-pointer transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-gray-900">{batch.strategy_name}</p>
                      <p className="text-sm text-gray-500">{new Date(batch.created_at).toLocaleString()}</p>
                      <p className="text-sm text-gray-600 mt-1">{batch.trade_count} trades</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(batch.status)}`}>
                      {batch.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
