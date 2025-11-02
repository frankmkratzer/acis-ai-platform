'use client'

import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import type { Client, Portfolio } from '@/types'

export default function PortfolioPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const clientId = parseInt(params.clientId as string)
  const accountHash = searchParams.get('account')

  const [client, setClient] = useState<Client | null>(null)
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (clientId && accountHash) {
      fetchData()
    }
  }, [clientId, accountHash])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [clientData, portfolioData] = await Promise.all([
        api.clients.get(clientId),
        api.schwab.getPortfolio(clientId, accountHash!),
      ])

      setClient(clientData)
      setPortfolio(portfolioData)
    } catch (err: any) {
      console.error('Failed to fetch portfolio:', err)
      setError(err.detail || 'Failed to load portfolio')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading portfolio...</p>
        </div>
      </div>
    )
  }

  if (error || !client || !portfolio) {
    return (
      <div className="space-y-4">
        <Link href={`/clients/${clientId}`} className="text-blue-600 hover:text-blue-700">
          ← Back to Client
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-red-800">Error Loading Portfolio</h3>
          <p className="mt-2 text-sm text-red-700">{error || 'Portfolio not found'}</p>
        </div>
      </div>
    )
  }

  const totalValue = portfolio.summary?.total_value || 0
  const cash = portfolio.summary?.cash || 0
  const invested = portfolio.summary?.invested || 0
  const positions = portfolio.positions || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href={`/clients/${clientId}`}
          className="text-blue-600 hover:text-blue-700 text-sm"
        >
          ← Back to Client
        </Link>
        <div className="mt-4">
          <h1 className="text-3xl font-bold text-gray-900">
            Portfolio - {client.first_name} {client.last_name}
          </h1>
          <p className="mt-2 text-gray-600">
            Account: {accountHash?.substring(0, 16)}...
          </p>
        </div>
      </div>

      {/* Account Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Total Value</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Invested</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            ${invested.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Cash</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
            ${cash.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Positions</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{positions.length}</p>
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Holdings</h2>
        </div>
        {positions.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            No positions in portfolio
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Price
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Current Price
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Market Value
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    % of Portfolio
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P/L
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P/L %
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {positions.map((position: any) => {
                  const currentPrice = position.current_value / position.quantity
                  const gainPercent = (position.total_gain / position.cost_basis) * 100
                  const portfolioPercent = (position.current_value / totalValue) * 100

                  return (
                    <tr key={position.symbol} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {position.symbol}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {position.quantity?.toLocaleString() || '0'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        ${position.average_price?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        ${currentPrice?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        ${position.current_value?.toLocaleString('en-US', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        }) || '0.00'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                        {portfolioPercent?.toFixed(2) || '0.00'}%
                      </td>
                      <td
                        className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                          position.total_gain >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {position.total_gain >= 0 ? '+' : ''}$
                        {position.total_gain?.toFixed(2) || '0.00'}
                      </td>
                      <td
                        className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                          gainPercent >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {gainPercent >= 0 ? '+' : ''}
                        {gainPercent?.toFixed(2) || '0.00'}%
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex space-x-4">
        <Link
          href={`/trading?client=${clientId}&account=${accountHash}`}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Generate Trade Recommendations
        </Link>
        <button className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
          Export Portfolio
        </button>
      </div>
    </div>
  )
}
