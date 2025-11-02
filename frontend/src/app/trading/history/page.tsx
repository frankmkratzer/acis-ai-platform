'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '@/lib/api'
import type { TradeExecution } from '@/types'

export default function TradeHistoryPage() {
  const [executions, setExecutions] = useState<TradeExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')

  useEffect(() => {
    fetchExecutions()
  }, [statusFilter])

  const fetchExecutions = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.trading.getExecutions(
        undefined,
        statusFilter || undefined,
        200
      )
      setExecutions(data.executions)
    } catch (err: any) {
      console.error('Failed to fetch executions:', err)
      setError(err.detail || 'Failed to load trade history')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading trade history...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/trading" className="text-blue-600 hover:text-blue-700">
          ← Back to Trading
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-red-800">Error Loading History</h3>
          <p className="mt-2 text-sm text-red-700">{error}</p>
          <button
            onClick={fetchExecutions}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const statusCounts = {
    total: executions.length,
    submitted: executions.filter((e) => e.status === 'submitted').length,
    filled: executions.filter((e) => e.status === 'filled').length,
    failed: executions.filter((e) => e.status === 'failed').length,
    cancelled: executions.filter((e) => e.status === 'cancelled').length,
  }

  const totalVolume = executions
    .filter((e) => e.price && e.status !== 'failed')
    .reduce((sum, e) => sum + (e.shares * (e.price || 0)), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/trading" className="text-blue-600 hover:text-blue-700 text-sm">
          ← Back to Trading
        </Link>
        <div className="mt-4">
          <h1 className="text-3xl font-bold text-gray-900">Trade History</h1>
          <p className="mt-2 text-gray-600">View all executed trades and their status</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Total number of trade executions across all clients and statuses"
        >
          <p className="text-sm font-medium text-gray-500">Total Trades</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{statusCounts.total}</p>
        </div>
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Trades submitted to brokerage and awaiting fill"
        >
          <p className="text-sm font-medium text-gray-500">Submitted</p>
          <p className="mt-2 text-3xl font-bold text-blue-600">{statusCounts.submitted}</p>
        </div>
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Successfully executed trades with confirmed fill prices"
        >
          <p className="text-sm font-medium text-gray-500">Filled</p>
          <p className="mt-2 text-3xl font-bold text-green-600">{statusCounts.filled}</p>
        </div>
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Trade executions that failed due to insufficient funds, market conditions, or other errors"
        >
          <p className="text-sm font-medium text-gray-500">Failed</p>
          <p className="mt-2 text-3xl font-bold text-red-600">{statusCounts.failed}</p>
        </div>
        <div
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
          title="Total dollar value of all filled trades (excludes failed trades)"
        >
          <p className="text-sm font-medium text-gray-500">Total Volume</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            ${(totalVolume / 1000000).toFixed(2)}M
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-gray-700">Filter by Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            title="Filter trade history by execution status"
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Status</option>
            <option value="submitted">Submitted</option>
            <option value="filled">Filled</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button
            onClick={() => setStatusFilter('')}
            title="Reset status filter to show all trades"
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900"
          >
            Clear Filter
          </button>
        </div>
      </div>

      {/* Trade History Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        {executions.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
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
            <h3 className="mt-4 text-lg font-medium text-gray-900">No trade executions yet</h3>
            <p className="mt-2 text-sm text-gray-500">
              Execute approved recommendations to see trades here.
            </p>
            <Link
              href="/trading"
              className="mt-6 inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Go to Trading
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Shares
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Price
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Value
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Order Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Order ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {executions.map((execution) => (
                  <tr key={execution.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {execution.symbol}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          execution.action === 'BUY'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {execution.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {execution.shares.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {execution.price ? `$${execution.price.toFixed(2)}` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {execution.price
                        ? `$${(execution.shares * execution.price).toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                          })}`
                        : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
                      {execution.order_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          execution.status === 'filled'
                            ? 'bg-green-100 text-green-800'
                            : execution.status === 'submitted'
                            ? 'bg-blue-100 text-blue-800'
                            : execution.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : execution.status === 'cancelled'
                            ? 'bg-gray-100 text-gray-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {execution.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                      {execution.order_id || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {execution.executed_at
                        ? new Date(execution.executed_at).toLocaleString()
                        : new Date(execution.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Export */}
      {executions.length > 0 && (
        <div className="flex justify-end">
          <button
            title="Export trade history to CSV file for external analysis"
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            Export to CSV
          </button>
        </div>
      )}
    </div>
  )
}
