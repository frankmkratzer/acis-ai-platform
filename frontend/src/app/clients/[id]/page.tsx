'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import AccountFormModal from '@/components/AccountFormModal'
import ClientFormModal from '@/components/ClientFormModal'
import TradeModal from '@/components/TradeModal'
import AutonomousSettingsPanel from '@/components/AutonomousSettingsPanel'
import type { Client, BrokerageAccount, Portfolio } from '@/types'

export default function ClientDetailPage() {
  const params = useParams()
  const clientId = parseInt(params.id as string)

  const [client, setClient] = useState<Client | null>(null)
  const [accounts, setAccounts] = useState<BrokerageAccount[]>([])
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedAccount, setSelectedAccount] = useState<BrokerageAccount | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'autonomous'>('overview')

  // Modal states
  const [showAccountModal, setShowAccountModal] = useState(false)
  const [showClientModal, setShowClientModal] = useState(false)
  const [editingAccount, setEditingAccount] = useState<BrokerageAccount | null>(null)

  // Trade modal states
  const [showTradeModal, setShowTradeModal] = useState(false)
  const [tradeSymbol, setTradeSymbol] = useState('')
  const [tradeQuantity, setTradeQuantity] = useState(0)
  const [tradePrice, setTradePrice] = useState(0)
  const [tradeType, setTradeType] = useState<'BUY' | 'SELL'>('BUY')

  useEffect(() => {
    if (clientId) {
      fetchClientData()
    }
  }, [clientId])

  const fetchClientData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [clientData, accountsData] = await Promise.all([
        api.clients.get(clientId),
        api.brokerages.getClientAccounts(clientId),
      ])

      setClient(clientData)
      setAccounts(accountsData)

      // Auto-select first account and load portfolio
      if (accountsData.length > 0) {
        setSelectedAccount(accountsData[0])
        await fetchPortfolio(accountsData[0].account_hash)
      }
    } catch (err: any) {
      console.error('Failed to fetch client data:', err)
      setError(err.detail || 'Failed to load client data')
    } finally {
      setLoading(false)
    }
  }

  const fetchPortfolio = async (accountHash?: string) => {
    try {
      const portfolioData = await api.schwab.getPortfolio(clientId, accountHash)
      setPortfolio(portfolioData)
    } catch (err: any) {
      console.error('Failed to fetch portfolio:', err)
      // Don't set error, just log it - portfolio might not be connected yet
    }
  }

  const handleAddAccount = () => {
    setEditingAccount(null)
    setShowAccountModal(true)
  }

  const handleEditAccount = (account: BrokerageAccount) => {
    setEditingAccount(account)
    setShowAccountModal(true)
  }

  const handleDeleteAccount = async (accountId: number) => {
    if (!confirm('Are you sure you want to delete this brokerage account? This action cannot be undone.')) {
      return
    }

    try {
      await api.brokerages.deleteAccount(accountId)
      await fetchClientData()
    } catch (err: any) {
      alert(`Failed to delete account: ${err.detail || err.message}`)
    }
  }

  const handleAccountSaved = async () => {
    await fetchClientData()
  }

  const handleEditClient = () => {
    setShowClientModal(true)
  }

  const handleClientSaved = async () => {
    await fetchClientData()
  }

  const handleDeleteClient = async () => {
    if (!confirm('Are you sure you want to delete this client? This will also delete all associated accounts and data. This action cannot be undone.')) {
      return
    }

    try {
      await api.clients.delete(clientId)
      window.location.href = '/clients'
    } catch (err: any) {
      alert(`Failed to delete client: ${err.detail || err.message}`)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading client details...</p>
        </div>
      </div>
    )
  }

  const handleBuy = (symbol: string, currentPrice: number) => {
    setTradeSymbol(symbol)
    setTradePrice(currentPrice)
    setTradeQuantity(0)
    setTradeType('BUY')
    setShowTradeModal(true)
  }

  const handleSell = (symbol: string, currentQuantity: number, currentPrice: number) => {
    setTradeSymbol(symbol)
    setTradeQuantity(currentQuantity)
    setTradePrice(currentPrice)
    setTradeType('SELL')
    setShowTradeModal(true)
  }

  const handleTradeSuccess = async () => {
    // Reload portfolio after successful trade
    if (selectedAccount?.account_hash) {
      await fetchPortfolio(selectedAccount.account_hash)
    }
  }

  if (error || !client) {
    return (
      <div className="space-y-4">
        <Link href="/clients" className="text-blue-600 hover:text-blue-700">
          ← Back to Clients
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-red-800">Error Loading Client</h3>
          <p className="mt-2 text-sm text-red-700">{error || 'Client not found'}</p>
        </div>
      </div>
    )
  }

  const totalValue = portfolio?.summary?.total_value || 0
  const cash = portfolio?.summary?.cash || 0
  const positions = portfolio?.positions || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/clients" className="text-blue-600 hover:text-blue-700 text-sm">
          ← Back to Clients
        </Link>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {client.first_name} {client.last_name}
            </h1>
            <p className="mt-2 text-gray-600">{client.email}</p>
          </div>
          <div className="flex items-center space-x-3">
            <span
              className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium ${
                client.is_active
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {client.is_active ? 'Active' : 'Inactive'}
            </span>
            <Link
              href={`/clients/${clientId}/portfolio-health`}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
            >
              Portfolio Health
            </Link>
            <Link
              href={`/clients/${clientId}/trading`}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Trading
            </Link>
            <button
              onClick={handleEditClient}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Edit Client
            </button>
            <button
              onClick={handleDeleteClient}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Delete Client
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'overview'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Portfolio Overview
          </button>
          <button
            onClick={() => setActiveTab('autonomous')}
            className={`whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'autonomous'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Autonomous Trading
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' ? (
        <>
          {/* Client Info */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-sm font-medium text-gray-500">Phone</p>
              <p className="mt-2 text-lg text-gray-900">{client.phone || '-'}</p>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-sm font-medium text-gray-500">Risk Tolerance</p>
              <p className="mt-2 text-lg text-gray-900 capitalize">
                {client.risk_tolerance || '-'}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-sm font-medium text-gray-500">Brokerage Accounts</p>
              <p className="mt-2 text-lg text-gray-900">{accounts.length}</p>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-sm font-medium text-gray-500">Member Since</p>
              <p className="mt-2 text-lg text-gray-900">
                {new Date(client.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

      {/* Brokerage Accounts */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Brokerage Accounts</h2>
          <button
            onClick={handleAddAccount}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center space-x-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>Add Account</span>
          </button>
        </div>
        {accounts.length === 0 ? (
          <div className="px-6 py-8 text-center text-gray-500">
            No brokerage accounts yet. Click "Add Account" to link a brokerage account.
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {accounts.map((account) => (
              <div
                key={account.id}
                className={`px-6 py-4 cursor-pointer hover:bg-gray-50 ${
                  selectedAccount?.id === account.id ? 'bg-blue-50' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div
                    onClick={() => {
                      setSelectedAccount(account)
                      fetchPortfolio(account.account_hash)
                    }}
                    className="flex-1"
                  >
                    <div className="flex items-center space-x-3">
                      <p className="text-sm font-medium text-gray-900">
                        Account {account.account_number}
                      </p>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          account.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {account.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 capitalize mt-1">{account.account_type}</p>
                    {account.notes && (
                      <p className="text-xs text-gray-400 mt-1">{account.notes}</p>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleEditAccount(account)
                      }}
                      className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                      Edit
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteAccount(account.id)
                      }}
                      className="px-3 py-1.5 text-sm bg-red-100 text-red-800 rounded hover:bg-red-200"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Portfolio Overview */}
      {selectedAccount && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-sm font-medium text-gray-500">Total Account Value</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <p className="text-sm font-medium text-gray-500">Cash Balance</p>
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
          {positions.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Current Positions</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Symbol
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Shares
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
                        P/L
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {positions.map((position: any) => {
                      const currentPrice = position.current_value / position.quantity
                      const gainPercent = (position.total_gain / position.cost_basis) * 100

                      return (
                        <tr key={position.symbol}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {position.symbol}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            {position.quantity}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${position.average_price?.toFixed(2) || '0.00'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${currentPrice?.toFixed(2) || '0.00'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                            ${position.current_value?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                          </td>
                          <td
                            className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                              position.total_gain >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}
                          >
                            ${position.total_gain?.toFixed(2) || '0.00'} (
                            {gainPercent >= 0 ? '+' : ''}
                            {gainPercent?.toFixed(2) || '0.00'}%)
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                            <div className="flex justify-center space-x-2">
                              <button
                                onClick={() => handleBuy(position.symbol, currentPrice)}
                                className="px-3 py-1 text-xs font-medium text-green-700 bg-green-100 rounded hover:bg-green-200 transition-colors"
                              >
                                Buy
                              </button>
                              <button
                                onClick={() => handleSell(position.symbol, position.quantity, currentPrice)}
                                className="px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200 transition-colors"
                              >
                                Sell
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex space-x-4">
            <Link
              href={`/trading?client=${clientId}&account=${selectedAccount.account_hash}`}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Generate Recommendations
            </Link>
          </div>
        </div>
      )}
        </>
      ) : (
        /* Autonomous Trading Tab */
        <div>
          <AutonomousSettingsPanel clientId={clientId} />
        </div>
      )}

      {/* Modals */}
      <AccountFormModal
        isOpen={showAccountModal}
        onClose={() => {
          setShowAccountModal(false)
          setEditingAccount(null)
        }}
        clientId={clientId}
        account={editingAccount}
        onSave={handleAccountSaved}
      />

      <ClientFormModal
        isOpen={showClientModal}
        onClose={() => setShowClientModal(false)}
        client={client}
        onSave={handleClientSaved}
      />

      {selectedAccount && (
        <TradeModal
          isOpen={showTradeModal}
          onClose={() => setShowTradeModal(false)}
          symbol={tradeSymbol}
          currentQuantity={tradeQuantity}
          currentPrice={tradePrice}
          accountHash={selectedAccount.account_hash || ''}
          clientId={clientId}
          tradeType={tradeType}
          onSuccess={handleTradeSuccess}
        />
      )}
    </div>
  )
}
