'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

// Simple API client
const apiClient = axios.create({
  baseURL: 'http://192.168.50.234:8000',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  auth: { username: 'admin@acis-ai.com', password: 'admin123' },
})

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

export default function SchwabOAuthPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null)
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null)
  const [callbackUrl, setCallbackUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Load clients on mount
  useEffect(() => {
    loadClients()
  }, [])

  // Load token status when client is selected
  useEffect(() => {
    if (selectedClientId) {
      loadTokenStatus(selectedClientId)
    }
  }, [selectedClientId])

  const loadClients = async () => {
    try {
      const response = await apiClient.get('/api/clients/?skip=0&limit=100')
      setClients(response.data)
      if (response.data.length > 0) {
        setSelectedClientId(response.data[0].client_id)
      }
    } catch (error) {
      console.error('Failed to load clients:', error)
      showMessage('error', 'Failed to load clients')
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

  const handleStartOAuth = () => {
    if (!selectedClientId) {
      showMessage('error', 'Please select a client')
      return
    }

    // Open Schwab OAuth in new window
    const authUrl = `http://192.168.50.234:8000/api/schwab/authorize/${selectedClientId}`
    window.open(authUrl, '_blank', 'width=600,height=800')

    showMessage('success', 'OAuth window opened. After authorizing, paste the callback URL below.')
  }

  const handleManualCallback = async () => {
    if (!callbackUrl.trim()) {
      showMessage('error', 'Please enter the callback URL')
      return
    }

    setLoading(true)
    try {
      const response = await apiClient.post('/api/schwab/callback/manual', { callback_url: callbackUrl })

      showMessage('success', `Successfully connected Schwab account for client ${response.data.client_id}`)
      setCallbackUrl('')

      // Reload token status
      if (selectedClientId) {
        await loadTokenStatus(selectedClientId)
      }
    } catch (error: any) {
      console.error('Failed to process callback:', error)
      showMessage('error', error.response?.data?.detail || 'Failed to process callback URL')
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshToken = async () => {
    if (!selectedClientId) {
      showMessage('error', 'Please select a client')
      return
    }

    setLoading(true)
    try {
      await apiClient.post(`/api/schwab/refresh/${selectedClientId}`)
      showMessage('success', 'Token refreshed successfully')

      // Reload token status
      await loadTokenStatus(selectedClientId)
    } catch (error: any) {
      console.error('Failed to refresh token:', error)
      showMessage('error', error.response?.data?.detail || 'Failed to refresh token')
    } finally {
      setLoading(false)
    }
  }

  const handleRevokeToken = async () => {
    if (!selectedClientId) {
      showMessage('error', 'Please select a client')
      return
    }

    if (!confirm('Are you sure you want to disconnect this Schwab account?')) {
      return
    }

    setLoading(true)
    try {
      await apiClient.delete(`/api/schwab/revoke/${selectedClientId}`)
      showMessage('success', 'Schwab account disconnected')

      // Reload token status
      await loadTokenStatus(selectedClientId)
    } catch (error: any) {
      console.error('Failed to revoke token:', error)
      showMessage('error', error.response?.data?.detail || 'Failed to revoke token')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Schwab OAuth Management</h1>

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
          <h2 className="text-xl font-semibold mb-4">OAuth Actions</h2>

          <div className="space-y-4">
            {/* Start OAuth Flow */}
            <div>
              <button
                onClick={handleStartOAuth}
                disabled={!selectedClientId || loading}
                className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
              >
                1. Start OAuth Flow (Opens New Window)
              </button>
              <p className="text-sm text-gray-500 mt-2">
                Opens Schwab authorization page. After approving, copy the callback URL.
              </p>
            </div>

            {/* Manual Callback URL */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                2. Paste Callback URL from Schwab
              </label>
              <textarea
                value={callbackUrl}
                onChange={(e) => setCallbackUrl(e.target.value)}
                placeholder="https://localhost:8000/api/schwab/callback?code=...&state=..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent h-24"
                disabled={loading}
              />
              <button
                onClick={handleManualCallback}
                disabled={!callbackUrl.trim() || loading}
                className="mt-2 w-full bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {loading ? 'Processing...' : 'Process Callback URL'}
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
                  disabled={loading}
                  className="w-full bg-yellow-600 text-white px-6 py-3 rounded-lg hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {loading ? 'Refreshing...' : 'Refresh Token'}
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
                  disabled={loading}
                  className="w-full bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {loading ? 'Disconnecting...' : 'Disconnect Schwab Account'}
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
            <li>2. Click "Start OAuth Flow" - a new window will open with Schwab's authorization page</li>
            <li>3. Log in to your Schwab account and approve the access request</li>
            <li>4. After approving, Schwab will redirect to a URL (it may show an error - that's OK!)</li>
            <li>5. Copy the entire URL from your browser's address bar</li>
            <li>6. Paste the URL in the "Callback URL" field above and click "Process Callback URL"</li>
            <li>7. The token will be stored and you can now access Schwab account data</li>
          </ol>

          <div className="mt-4 pt-4 border-t border-blue-200">
            <h4 className="font-semibold text-blue-900 mb-2">Note:</h4>
            <p className="text-sm text-blue-800">
              Tokens are automatically refreshed when needed. You can manually refresh or disconnect using the buttons above.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
