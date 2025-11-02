'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import axios from 'axios'
import BrokerageFormModal from '@/components/BrokerageFormModal'

// Simple API client
const apiClient = axios.create({
  baseURL: 'http://192.168.50.234:8000',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  auth: { username: 'admin@acis-ai.com', password: 'admin123' },
})

interface Brokerage {
  brokerage_id: number
  name: string
  display_name: string | null
  supports_live_trading: boolean
  supports_paper_trading: boolean
  api_type: string | null
  status: string
  created_at: string
  updated_at: string | null
}

interface Client {
  client_id: number
  name: string
  email: string
}

interface TokenStatus {
  client_id: number
  connected: boolean
  expired?: boolean
  expires_at?: string
  created_at?: string
  updated_at?: string
  message?: string
}

export default function BrokerageDetailPage() {
  const params = useParams()
  const router = useRouter()
  const brokerageId = Number(params.id)

  const [brokerage, setBrokerage] = useState<Brokerage | null>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null)
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null)
  const [callbackUrl, setCallbackUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)

  useEffect(() => {
    loadBrokerage()
    loadClients()
  }, [brokerageId])

  useEffect(() => {
    if (selectedClientId && brokerage?.name === 'schwab') {
      loadTokenStatus(selectedClientId)
    }
  }, [selectedClientId, brokerage])

  const loadBrokerage = async () => {
    try {
      const response = await apiClient.get(`/api/brokerages/${brokerageId}`)
      setBrokerage(response.data)
    } catch (error: any) {
      console.error('Failed to load brokerage:', error)
      showMessage('error', 'Failed to load brokerage details')
    } finally {
      setLoading(false)
    }
  }

  const loadClients = async () => {
    try {
      const response = await apiClient.get('/api/clients/?skip=0&limit=100')
      setClients(response.data)
      if (response.data.length > 0) {
        setSelectedClientId(response.data[0].client_id)
      }
    } catch (error) {
      console.error('Failed to load clients:', error)
    }
  }

  const loadTokenStatus = async (clientId: number) => {
    try {
      const response = await apiClient.get(`/api/schwab/status/${clientId}`)
      setTokenStatus(response.data)
    } catch (error) {
      console.error('Failed to load token status:', error)
      setTokenStatus(null)
    }
  }

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 5000)
  }

  const handleStartOAuth = async () => {
    if (!selectedClientId || brokerage?.name !== 'schwab') {
      showMessage('error', 'Please select a client')
      return
    }

    try {
      // Try to start ngrok (optional - will warn if it fails but continue)
      try {
        const ngrokResult = await apiClient.post('/api/schwab/ngrok/start')

        if (ngrokResult.data.already_running) {
          showMessage('success', 'Ngrok is already running')
        } else {
          showMessage('success', `Ngrok started on ${ngrokResult.data.domain}`)
          // Wait a moment for ngrok to fully initialize
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
      } catch (ngrokError: any) {
        console.warn('Ngrok auto-start failed:', ngrokError)
        // Continue anyway - user might have ngrok running already
        showMessage('success', 'Make sure ngrok is running at acis.ngrok.app')
      }

      // Open OAuth window
      const authUrl = `http://192.168.50.234:8000/api/schwab/authorize/${selectedClientId}`
      window.open(authUrl, '_blank', 'width=600,height=800')
      showMessage('success', 'OAuth window opened. After authorizing, paste the callback URL below.')
    } catch (error: any) {
      console.error('Failed to start OAuth:', error)
      showMessage('error', `Failed to start OAuth: ${error.message}`)
    }
  }

  const handleManualCallback = async () => {
    if (!callbackUrl.trim()) {
      showMessage('error', 'Please enter the callback URL')
      return
    }

    setActionLoading(true)
    try {
      const response = await apiClient.post('/api/schwab/callback/manual', { callback_url: callbackUrl })
      showMessage('success', `Successfully connected ${brokerage?.display_name} account for client ${response.data.client_id}`)
      setCallbackUrl('')

      if (selectedClientId) {
        await loadTokenStatus(selectedClientId)
      }
    } catch (error: any) {
      console.error('Failed to process callback:', error)
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to process callback URL'
      showMessage('error', typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage))
    } finally {
      setActionLoading(false)
    }
  }

  const handleRefreshToken = async () => {
    if (!selectedClientId || brokerage?.name !== 'schwab') {
      showMessage('error', 'Please select a client')
      return
    }

    setActionLoading(true)
    try {
      await apiClient.post(`/api/schwab/refresh/${selectedClientId}`)
      showMessage('success', 'Token refreshed successfully')
      await loadTokenStatus(selectedClientId)
    } catch (error: any) {
      console.error('Failed to refresh token:', error)
      showMessage('error', error.response?.data?.detail || 'Failed to refresh token')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRevokeToken = async () => {
    if (!selectedClientId || brokerage?.name !== 'schwab') {
      showMessage('error', 'Please select a client')
      return
    }

    if (!confirm(`Are you sure you want to disconnect this ${brokerage?.display_name} account?`)) {
      return
    }

    setActionLoading(true)
    try {
      await apiClient.delete(`/api/schwab/revoke/${selectedClientId}`)
      showMessage('success', `${brokerage?.display_name} account disconnected`)
      await loadTokenStatus(selectedClientId)
    } catch (error: any) {
      console.error('Failed to revoke token:', error)
      showMessage('error', error.response?.data?.detail || 'Failed to revoke token')
    } finally {
      setActionLoading(false)
    }
  }

  const handleEdit = () => {
    setShowEditModal(true)
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this brokerage? This action cannot be undone.')) {
      return
    }

    try {
      await apiClient.delete(`/api/brokerages/${brokerageId}`)
      showMessage('success', 'Brokerage deleted successfully')
      setTimeout(() => {
        router.push('/brokerages')
      }, 1500)
    } catch (error: any) {
      console.error('Failed to delete brokerage:', error)
      showMessage('error', error.response?.data?.detail || 'Failed to delete brokerage')
    }
  }

  const handleModalSave = () => {
    loadBrokerage()
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="max-w-4xl mx-auto text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
          <p className="mt-2 text-gray-600">Loading brokerage details...</p>
        </div>
      </div>
    )
  }

  if (!brokerage) {
    return (
      <div className="p-8">
        <div className="max-w-4xl mx-auto text-center py-12">
          <p className="text-red-600">Brokerage not found</p>
          <Link href="/brokerages" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
            ← Back to Brokerages
          </Link>
        </div>
      </div>
    )
  }

  const isSchwab = brokerage.name === 'schwab'

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link href="/brokerages" className="text-blue-600 hover:text-blue-700">
            ← Back to Brokerages
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {brokerage.display_name || brokerage.name}
            </h1>
            <p className="mt-2 text-gray-600">Manage OAuth connections and settings</p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={handleEdit}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Edit Brokerage
            </button>
            <button
              onClick={handleDelete}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Delete
            </button>
          </div>
        </div>

        {/* Message Alert */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {message.text}
          </div>
        )}

        {/* Brokerage Info */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Brokerage Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-gray-600">Name:</span>
              <span className="ml-2 font-medium">{brokerage.name}</span>
            </div>
            <div>
              <span className="text-gray-600">Status:</span>
              <span className={`ml-2 px-2 py-1 rounded text-sm font-medium ${
                brokerage.status === 'active'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {brokerage.status}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Live Trading:</span>
              <span className={`ml-2 font-medium ${
                brokerage.supports_live_trading ? 'text-green-600' : 'text-gray-400'
              }`}>
                {brokerage.supports_live_trading ? 'Yes' : 'No'}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Paper Trading:</span>
              <span className={`ml-2 font-medium ${
                brokerage.supports_paper_trading ? 'text-green-600' : 'text-gray-400'
              }`}>
                {brokerage.supports_paper_trading ? 'Yes' : 'No'}
              </span>
            </div>
            {brokerage.api_type && (
              <div>
                <span className="text-gray-600">API Type:</span>
                <span className="ml-2 font-medium">{brokerage.api_type}</span>
              </div>
            )}
          </div>
        </div>

        {/* OAuth Management - Only for Schwab */}
        {isSchwab && (
          <>
            {/* Client Selection */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Select Client</h2>
              <select
                value={selectedClientId || ''}
                onChange={(e) => setSelectedClientId(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Select a client...</option>
                {clients.map((client) => (
                  <option key={client.client_id} value={client.client_id}>
                    {client.name} ({client.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Token Status */}
            {selectedClientId && tokenStatus && (
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 className="text-xl font-semibold mb-4">Connection Status</h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      tokenStatus.connected
                        ? tokenStatus.expired
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {tokenStatus.connected
                        ? tokenStatus.expired ? 'Expired' : 'Connected'
                        : 'Not Connected'
                      }
                    </span>
                  </div>

                  {tokenStatus.connected && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Expires At:</span>
                        <span className="text-gray-900">{formatDate(tokenStatus.expires_at!)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Created At:</span>
                        <span className="text-gray-900">{formatDate(tokenStatus.created_at!)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Last Updated:</span>
                        <span className="text-gray-900">{formatDate(tokenStatus.updated_at!)}</span>
                      </div>
                    </>
                  )}

                  {!tokenStatus.connected && (
                    <p className="text-gray-500 text-sm">{tokenStatus.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* OAuth Actions */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">OAuth Management</h2>

              <div className="space-y-4">
                {/* Start OAuth Flow */}
                <div>
                  <button
                    onClick={handleStartOAuth}
                    disabled={!selectedClientId || actionLoading}
                    className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    1. Start OAuth Flow (Opens New Window)
                  </button>
                  <p className="text-sm text-gray-500 mt-2">
                    Opens {brokerage.display_name} authorization page. After approving, copy the callback URL.
                  </p>
                </div>

                {/* Manual Callback URL */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    2. Paste Callback URL from {brokerage.display_name}
                  </label>
                  <textarea
                    value={callbackUrl}
                    onChange={(e) => setCallbackUrl(e.target.value)}
                    placeholder="https://localhost:8000/api/schwab/callback?code=...&state=..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent h-24"
                    disabled={actionLoading}
                  />
                  <button
                    onClick={handleManualCallback}
                    disabled={!callbackUrl.trim() || actionLoading}
                    className="mt-2 w-full bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    {actionLoading ? 'Processing...' : 'Process Callback URL'}
                  </button>
                  <p className="text-sm text-gray-500 mt-2">
                    The URL should contain 'code' and 'state' parameters.
                  </p>
                </div>

                {/* Refresh Token */}
                {tokenStatus?.connected && (
                  <div className="pt-4 border-t border-gray-200">
                    <button
                      onClick={handleRefreshToken}
                      disabled={actionLoading}
                      className="w-full bg-yellow-600 text-white px-6 py-3 rounded-lg hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                    >
                      {actionLoading ? 'Refreshing...' : 'Refresh Token'}
                    </button>
                    <p className="text-sm text-gray-500 mt-2">
                      Manually refresh the OAuth token (normally happens automatically).
                    </p>
                  </div>
                )}

                {/* Revoke Token */}
                {tokenStatus?.connected && (
                  <div className="pt-4 border-t border-gray-200">
                    <button
                      onClick={handleRevokeToken}
                      disabled={actionLoading}
                      className="w-full bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                    >
                      {actionLoading ? 'Disconnecting...' : `Disconnect ${brokerage.display_name} Account`}
                    </button>
                    <p className="text-sm text-gray-500 mt-2">
                      Permanently disconnect and remove the OAuth token.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">How to Connect</h3>
              <ol className="space-y-2 text-sm text-blue-800">
                <li>1. Select a client from the dropdown above</li>
                <li>2. Click "Start OAuth Flow" - a new window will open with {brokerage.display_name}'s authorization page</li>
                <li>3. Log in to your {brokerage.display_name} account and approve the access request</li>
                <li>4. After approving, {brokerage.display_name} will redirect to a URL (it may show an error - that's OK!)</li>
                <li>5. Copy the entire URL from your browser's address bar</li>
                <li>6. Paste the URL in the "Callback URL" field above and click "Process Callback URL"</li>
                <li>7. The token will be stored and you can now access {brokerage.display_name} account data</li>
              </ol>

              <div className="mt-4 pt-4 border-t border-blue-200">
                <h4 className="font-semibold text-blue-900 mb-2">Note:</h4>
                <p className="text-sm text-blue-800">
                  Tokens are automatically refreshed when needed. You can manually refresh or disconnect using the buttons above.
                </p>
              </div>
            </div>
          </>
        )}

        {/* OAuth Not Supported */}
        {!isSchwab && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">OAuth Management</h3>
            <p className="text-gray-600">
              OAuth integration for {brokerage.display_name || brokerage.name} is not yet implemented.
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Only Schwab supports OAuth integration at this time.
            </p>
          </div>
        )}

        {/* Edit Modal */}
        <BrokerageFormModal
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          brokerage={brokerage}
          onSave={handleModalSave}
        />
      </div>
    </div>
  )
}
