'use client'

import { useState, useEffect } from 'react'
import { Settings, Save, AlertTriangle, RefreshCw } from 'lucide-react'
import api from '@/lib/api'
import Tooltip from './Tooltip'
import InlineHelp from './InlineHelp'

interface AutonomousSettings {
  client_id: number
  auto_trading_enabled: boolean
  trading_mode: 'paper' | 'live'
  risk_tolerance: 'conservative' | 'moderate' | 'aggressive'
  rebalance_frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'threshold'
  drift_threshold: number
  max_position_size: number
  allowed_strategies: string[]
  min_cash_balance: number
  tax_optimization_enabled: boolean
}

interface Props {
  clientId: number
}

export default function AutonomousSettingsPanel({ clientId }: Props) {
  const [settings, setSettings] = useState<AutonomousSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [syncSuccess, setSyncSuccess] = useState(false)
  const [syncedBalance, setSyncedBalance] = useState<{cash_balance: number, buying_power: number, account_value: number} | null>(null)

  useEffect(() => {
    fetchSettings()
  }, [clientId])

  const fetchSettings = async () => {
    try {
      setLoading(true)
      const data = await api.clients.getAutonomousSettings(clientId)
      setSettings(data)
    } catch (err: any) {
      setError(err.detail || 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!settings) return

    try {
      setSaving(true)
      setError(null)
      setSuccess(false)

      await api.clients.updateAutonomousSettings(clientId, settings)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: any) {
      setError(err.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSyncBalance = async () => {
    try {
      setSyncing(true)
      setError(null)
      setSyncSuccess(false)

      const result = await api.clients.syncBalanceFromSchwab(clientId)
      setSyncedBalance(result.synced_balance)
      setSyncSuccess(true)
      setTimeout(() => setSyncSuccess(false), 5000)
    } catch (err: any) {
      setError(err.detail || 'Failed to sync balance from Schwab')
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return <div className="animate-pulse bg-gray-100 h-96 rounded-lg"></div>
  }

  if (!settings) return null

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">Autonomous Trading Settings</h3>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          Settings saved successfully!
        </div>
      )}

      {syncSuccess && syncedBalance && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          Balance synced from Schwab: ${syncedBalance.cash_balance.toLocaleString()} cash,
          ${syncedBalance.account_value.toLocaleString()} total account value
        </div>
      )}

      {/* Sync Balance from Schwab Button */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <label className="font-medium text-gray-900">Sync Balance from Schwab</label>
            <p className="text-sm text-gray-600 mt-1">
              Fetch current Schwab account balance and set it as starting balance for paper trading & backtesting
            </p>
          </div>
          <button
            onClick={handleSyncBalance}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {/* Help Panel */}
        <InlineHelp
          title="Understanding Autonomous Trading Settings"
          variant="info"
          learnMoreLink="/docs/operations"
          content={
            <div>
              <p className="mb-2">
                These settings control how the AI manages this client's portfolio. Start with paper trading
                to test the system before switching to live trades.
              </p>
              <ul className="list-disc pl-5 space-y-1 text-sm">
                <li><strong>Paper Trading:</strong> Simulates trades without real money</li>
                <li><strong>Risk Tolerance:</strong> Conservative = lower volatility, Aggressive = higher returns potential</li>
                <li><strong>Drift Threshold:</strong> Triggers rebalance when portfolio deviates from target</li>
              </ul>
            </div>
          }
        />

        {/* Opt-in Toggle */}
        <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2">
            <label className="font-medium text-gray-900">Enable Autonomous Trading</label>
            <Tooltip content="When enabled, the AI will automatically generate and execute trade recommendations based on these settings. All trades are logged and can be reviewed." />
          </div>
          <div>
            <p className="text-sm text-gray-600 mt-1">Allow AI to manage this client's portfolio automatically</p>
          </div>
          <button
            onClick={() => setSettings({ ...settings, auto_trading_enabled: !settings.auto_trading_enabled })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.auto_trading_enabled ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.auto_trading_enabled ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>

        {/* Trading Mode */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Trading Mode</label>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setSettings({ ...settings, trading_mode: 'paper' })}
              className={`px-4 py-3 rounded-lg border-2 transition-colors ${
                settings.trading_mode === 'paper'
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-200 text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="font-medium">Paper Trading</div>
              <div className="text-xs mt-1">Simulated trades only</div>
            </button>
            <button
              onClick={() => setSettings({ ...settings, trading_mode: 'live' })}
              className={`px-4 py-3 rounded-lg border-2 transition-colors ${
                settings.trading_mode === 'live'
                  ? 'border-red-600 bg-red-50 text-red-700'
                  : 'border-gray-200 text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="font-medium">Live Trading</div>
              <div className="text-xs mt-1">Real money trades</div>
            </button>
          </div>
          {settings.trading_mode === 'live' && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              <strong>Warning:</strong> Live trading will execute real trades with real money
            </div>
          )}
        </div>

        {/* Risk Tolerance */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <label className="block text-sm font-medium text-gray-700">Risk Tolerance</label>
            <Tooltip content="Conservative minimizes volatility and drawdowns. Moderate balances risk/return. Aggressive maximizes growth potential with higher volatility." />
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(['conservative', 'moderate', 'aggressive'] as const).map((risk) => (
              <button
                key={risk}
                onClick={() => setSettings({ ...settings, risk_tolerance: risk })}
                className={`px-4 py-2 rounded-lg border-2 transition-colors ${
                  settings.risk_tolerance === risk
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-700 hover:border-gray-300'
                }`}
              >
                {risk.charAt(0).toUpperCase() + risk.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Rebalance Frequency */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <label className="block text-sm font-medium text-gray-700">Rebalance Frequency</label>
            <Tooltip content="How often the system checks and adjusts the portfolio. 'Threshold-based' only rebalances when drift exceeds the threshold, minimizing transaction costs." />
          </div>
          <select
            value={settings.rebalance_frequency}
            onChange={(e) => setSettings({ ...settings, rebalance_frequency: e.target.value as any })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="threshold">Threshold-based</option>
          </select>
        </div>

        {/* Drift Threshold */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Drift Threshold ({(settings.drift_threshold * 100).toFixed(0)}%)
            </label>
            <Tooltip content="Portfolio is rebalanced when actual allocation deviates from target by this percentage. Lower = more frequent rebalancing. Typical range: 3-10%." />
          </div>
          <input
            type="range"
            min="1"
            max="20"
            value={settings.drift_threshold * 100}
            onChange={(e) => setSettings({ ...settings, drift_threshold: parseInt(e.target.value) / 100 })}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">Trigger rebalance when position drifts beyond this percentage</p>
        </div>

        {/* Max Position Size */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Position Size ({(settings.max_position_size * 100).toFixed(0)}%)
          </label>
          <input
            type="range"
            min="1"
            max="25"
            value={settings.max_position_size * 100}
            onChange={(e) => setSettings({ ...settings, max_position_size: parseInt(e.target.value) / 100 })}
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">Maximum allocation to any single position</p>
        </div>

        {/* Min Cash Balance */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Cash Balance</label>
          <input
            type="number"
            value={settings.min_cash_balance}
            onChange={(e) => setSettings({ ...settings, min_cash_balance: parseFloat(e.target.value) })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            min="0"
            step="100"
          />
        </div>

        {/* Tax Optimization */}
        <div className="flex items-center justify-between">
          <div>
            <label className="font-medium text-gray-900">Tax-Loss Harvesting</label>
            <p className="text-sm text-gray-600 mt-1">Automatically harvest tax losses when opportunities arise</p>
          </div>
          <button
            onClick={() => setSettings({ ...settings, tax_optimization_enabled: !settings.tax_optimization_enabled })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              settings.tax_optimization_enabled ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              settings.tax_optimization_enabled ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>

        {/* Warning if enabled */}
        {settings.auto_trading_enabled && (
          <div className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-900">Autonomous Trading Enabled</p>
              <p className="text-xs text-yellow-700 mt-1">
                The AI system will automatically manage this client's portfolio according to these settings.
                All trades will be logged and can be reviewed in the trading history.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
