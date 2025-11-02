'use client'

import { useState } from 'react'
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Play,
  Shield,
  Database,
  TrendingUp,
  Key
} from 'lucide-react'
import api from '@/lib/api'

interface TestResult {
  name: string
  status: 'pending' | 'running' | 'passed' | 'failed'
  message?: string
  details?: any
}

export default function TestLiveTradingPage() {
  const [clientId, setClientId] = useState<string>('1')
  const [accountHash, setAccountHash] = useState<string>('')
  const [testing, setTesting] = useState(false)
  const [testResults, setTestResults] = useState<TestResult[]>([
    { name: 'OAuth Token Status', status: 'pending' },
    { name: 'Fetch Schwab Positions', status: 'pending' },
    { name: 'Sync Positions to Database', status: 'pending' },
    { name: 'Run Autonomous Rebalancer (Dry Run)', status: 'pending' },
  ])
  const [summary, setSummary] = useState<{ allPassed: boolean; timestamp: string } | null>(null)

  const updateTestResult = (index: number, updates: Partial<TestResult>) => {
    setTestResults(prev => {
      const newResults = [...prev]
      newResults[index] = { ...newResults[index], ...updates }
      return newResults
    })
  }

  const runTests = async () => {
    setTesting(true)
    setSummary(null)

    // Reset all tests to pending
    setTestResults([
      { name: 'OAuth Token Status', status: 'pending' },
      { name: 'Fetch Schwab Positions', status: 'pending' },
      { name: 'Sync Positions to Database', status: 'pending' },
      { name: 'Run Autonomous Rebalancer (Dry Run)', status: 'pending' },
    ])

    const cid = parseInt(clientId)
    let detectedAccountHash = accountHash

    try {
      // Auto-detect account hash if not provided
      if (!detectedAccountHash) {
        const accounts = await api.brokerages.getClientAccounts(cid)
        if (accounts.length === 0) {
          throw new Error('No brokerage accounts found for this client')
        }
        detectedAccountHash = accounts[0].account_hash || ''
      }

      // Test 1: OAuth Token Status
      updateTestResult(0, { status: 'running' })
      try {
        const tokenStatus = await api.schwab.getStatus(cid)
        if (tokenStatus.connected) {
          updateTestResult(0, {
            status: 'passed',
            message: 'OAuth token is valid and not expired',
            details: tokenStatus
          })
        } else {
          updateTestResult(0, {
            status: 'failed',
            message: 'No valid OAuth token found. Please complete Schwab OAuth flow.',
            details: tokenStatus
          })
          return
        }
      } catch (err: any) {
        updateTestResult(0, {
          status: 'failed',
          message: err.detail || err.message || 'Failed to check OAuth token'
        })
        return
      }

      // Test 2: Fetch Schwab Positions
      updateTestResult(1, { status: 'running' })
      let positions: any[] = []
      try {
        const portfolio = await api.schwab.getPortfolio(cid, detectedAccountHash)
        positions = portfolio.positions || []

        updateTestResult(1, {
          status: 'passed',
          message: `Successfully fetched ${positions.length} positions from Schwab API`,
          details: {
            positions: positions.length,
            totalValue: portfolio.total_value,
            accountHash: detectedAccountHash
          }
        })
      } catch (err: any) {
        updateTestResult(1, {
          status: 'failed',
          message: err.detail || err.message || 'Failed to fetch positions from Schwab'
        })
        return
      }

      // Test 3: Sync Positions to Database
      updateTestResult(2, { status: 'running' })
      try {
        const syncResult = await api.portfolioHealth.syncSchwabPositions(cid, detectedAccountHash)

        updateTestResult(2, {
          status: 'passed',
          message: `Successfully synced ${positions.length} positions to paper_positions table`,
          details: syncResult
        })
      } catch (err: any) {
        updateTestResult(2, {
          status: 'failed',
          message: err.detail || err.message || 'Failed to sync positions to database'
        })
        return
      }

      // Test 4: Run Autonomous Rebalancer (Dry Run)
      updateTestResult(3, { status: 'running' })
      try {
        const rebalanceResult = await api.autonomous.triggerRebalance(true, true)

        updateTestResult(3, {
          status: 'passed',
          message: 'Autonomous rebalancer simulation completed successfully',
          details: rebalanceResult
        })
      } catch (err: any) {
        // Note: Backend might not be fully implemented yet
        updateTestResult(3, {
          status: 'failed',
          message: err.detail || err.message || 'Rebalancer simulation failed'
        })
      }

      // Generate summary
      const allPassed = testResults.every(t => t.status === 'passed')
      setSummary({
        allPassed,
        timestamp: new Date().toISOString()
      })

    } catch (err: any) {
      console.error('Test flow error:', err)
    } finally {
      setTesting(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return <CheckCircle className="w-6 h-6 text-green-600" />
      case 'failed':
        return <XCircle className="w-6 h-6 text-red-600" />
      case 'running':
        return <Clock className="w-6 h-6 text-blue-600 animate-spin" />
      default:
        return <Clock className="w-6 h-6 text-gray-400" />
    }
  }

  const getTestIcon = (index: number) => {
    const icons = [
      <Key className="w-5 h-5" />,
      <TrendingUp className="w-5 h-5" />,
      <Database className="w-5 h-5" />,
      <Shield className="w-5 h-5" />
    ]
    return icons[index]
  }

  const allTestsPassed = testResults.every(t => t.status === 'passed')

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow-lg p-8 text-white">
        <h1 className="text-4xl font-bold mb-2">Live Trading Test Flow</h1>
        <p className="text-blue-100">
          Validate your entire live trading system before executing real trades
        </p>
      </div>

      {/* Configuration */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Test Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Client ID *
            </label>
            <input
              type="number"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              disabled={testing}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder="Enter client ID"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Account Hash (optional)
            </label>
            <input
              type="text"
              value={accountHash}
              onChange={(e) => setAccountHash(e.target.value)}
              disabled={testing}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
              placeholder="Auto-detect if empty"
            />
          </div>
        </div>
        <div className="mt-6">
          <button
            onClick={runTests}
            disabled={testing || !clientId}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            <Play className={`w-5 h-5 ${testing ? 'animate-pulse' : ''}`} />
            {testing ? 'Running Tests...' : 'Run Test Flow'}
          </button>
        </div>
      </div>

      {/* Test Results */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Test Results</h2>
        <div className="space-y-4">
          {testResults.map((test, index) => (
            <div
              key={index}
              className={`border-2 rounded-lg p-4 transition-all ${
                test.status === 'passed'
                  ? 'border-green-200 bg-green-50'
                  : test.status === 'failed'
                  ? 'border-red-200 bg-red-50'
                  : test.status === 'running'
                  ? 'border-blue-200 bg-blue-50'
                  : 'border-gray-200 bg-white'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1">
                  <div className={`p-2 rounded-lg ${
                    test.status === 'passed'
                      ? 'bg-green-100 text-green-600'
                      : test.status === 'failed'
                      ? 'bg-red-100 text-red-600'
                      : test.status === 'running'
                      ? 'bg-blue-100 text-blue-600'
                      : 'bg-gray-100 text-gray-400'
                  }`}>
                    {getTestIcon(index)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">{test.name}</h3>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        test.status === 'passed'
                          ? 'bg-green-100 text-green-700'
                          : test.status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : test.status === 'running'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-gray-100 text-gray-700'
                      }`}>
                        {test.status.toUpperCase()}
                      </span>
                    </div>
                    {test.message && (
                      <p className={`text-sm ${
                        test.status === 'failed' ? 'text-red-700' : 'text-gray-600'
                      }`}>
                        {test.message}
                      </p>
                    )}
                    {test.details && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                          View details
                        </summary>
                        <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                          {JSON.stringify(test.details, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
                <div className="ml-4">
                  {getStatusIcon(test.status)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className={`rounded-lg shadow-md p-6 ${
          allTestsPassed
            ? 'bg-green-50 border-2 border-green-300'
            : 'bg-red-50 border-2 border-red-300'
        }`}>
          <div className="flex items-start gap-4">
            {allTestsPassed ? (
              <CheckCircle className="w-12 h-12 text-green-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-12 h-12 text-red-600 flex-shrink-0" />
            )}
            <div className="flex-1">
              <h2 className={`text-2xl font-bold mb-2 ${
                allTestsPassed ? 'text-green-900' : 'text-red-900'
              }`}>
                {allTestsPassed
                  ? '✅ ALL TESTS PASSED - System Ready for Live Trading'
                  : '❌ SOME TESTS FAILED - Fix Issues Before Live Trading'
                }
              </h2>
              <p className={`text-sm mb-4 ${
                allTestsPassed ? 'text-green-700' : 'text-red-700'
              }`}>
                Test completed at {new Date(summary.timestamp).toLocaleString()}
              </p>

              {allTestsPassed && (
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm font-medium text-gray-900 mb-2">
                    Next Steps:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    <li>Verify client autonomous settings are correctly configured</li>
                    <li>Ensure trading mode is set to "live" (not "paper")</li>
                    <li>Enable autonomous trading for the client</li>
                    <li>Monitor the first few rebalancing cycles closely</li>
                  </ul>
                </div>
              )}

              {!allTestsPassed && (
                <div className="bg-white rounded-lg p-4 border border-red-200">
                  <p className="text-sm font-medium text-gray-900 mb-2">
                    Required Actions:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    {testResults.map((test, idx) =>
                      test.status === 'failed' && (
                        <li key={idx}>
                          <strong>{test.name}:</strong> {test.message}
                        </li>
                      )
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-medium mb-1">Important Notes:</p>
            <ul className="list-disc list-inside space-y-1 text-blue-800">
              <li>All tests run in <strong>dry-run mode</strong> - no real trades are executed</li>
              <li>This validates your OAuth connection, data flow, and rebalancer logic</li>
              <li>Run this test before enabling live trading for any client</li>
              <li>Re-run periodically to ensure system health</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
