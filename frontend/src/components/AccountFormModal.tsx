'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'
import type { BrokerageAccount, Brokerage } from '@/types'

interface Props {
  isOpen: boolean
  onClose: () => void
  clientId: number
  account?: BrokerageAccount | null
  onSave: () => void
}

export default function AccountFormModal({ isOpen, onClose, clientId, account, onSave }: Props) {
  const [brokerages, setBrokerages] = useState<Brokerage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    brokerage_id: account?.brokerage_id || 1,
    account_number: account?.account_number || '',
    account_type: account?.account_type || 'individual',
    account_hash: account?.account_hash || '',
    notes: account?.notes || '',
    is_active: account?.is_active !== undefined ? account.is_active : true,
  })

  useEffect(() => {
    if (isOpen) {
      fetchBrokerages()
      if (account) {
        setFormData({
          brokerage_id: account.brokerage_id,
          account_number: account.account_number,
          account_type: account.account_type,
          account_hash: account.account_hash,
          notes: account.notes || '',
          is_active: account.is_active,
        })
      }
    }
  }, [isOpen, account])

  const fetchBrokerages = async () => {
    try {
      const data = await api.brokerages.list()
      setBrokerages(data)
    } catch (err: any) {
      console.error('Failed to fetch brokerages:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (account) {
        // Update existing account
        await api.brokerages.updateAccount(account.id, formData)
      } else {
        // Create new account
        await api.brokerages.linkAccount(
          clientId,
          formData.brokerage_id,
          formData.account_number,
          formData.account_type,
          formData.account_hash,
          formData.notes
        )
      }
      onSave()
      onClose()
    } catch (err: any) {
      setError(err.detail || 'Failed to save account')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">
            {account ? 'Edit Account' : 'Add Brokerage Account'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Brokerage */}
          <div>
            <label htmlFor="brokerage_id" className="block text-sm font-medium text-gray-700 mb-1">
              Brokerage *
            </label>
            <select
              id="brokerage_id"
              name="brokerage_id"
              value={formData.brokerage_id}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {brokerages.map((brokerage) => (
                <option key={brokerage.brokerage_id} value={brokerage.brokerage_id}>
                  {brokerage.display_name || brokerage.name}
                </option>
              ))}
            </select>
          </div>

          {/* Account Number */}
          <div>
            <label htmlFor="account_number" className="block text-sm font-medium text-gray-700 mb-1">
              Account Number *
            </label>
            <input
              type="text"
              id="account_number"
              name="account_number"
              value={formData.account_number}
              onChange={handleChange}
              required
              placeholder="e.g., XXXX1234"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Account Type */}
          <div>
            <label htmlFor="account_type" className="block text-sm font-medium text-gray-700 mb-1">
              Account Type *
            </label>
            <select
              id="account_type"
              name="account_type"
              value={formData.account_type}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="individual">Individual</option>
              <option value="joint">Joint</option>
              <option value="ira">Traditional IRA</option>
              <option value="roth_ira">Roth IRA</option>
              <option value="sep_ira">SEP IRA</option>
              <option value="401k">401(k)</option>
              <option value="trust">Trust</option>
              <option value="corporate">Corporate</option>
            </select>
          </div>

          {/* Account Hash */}
          <div>
            <label htmlFor="account_hash" className="block text-sm font-medium text-gray-700 mb-1">
              Account Hash (Optional)
            </label>
            <input
              type="text"
              id="account_hash"
              name="account_hash"
              value={formData.account_hash}
              onChange={handleChange}
              placeholder="Schwab account hash"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              For Schwab OAuth connections
            </p>
          </div>

          {/* Notes */}
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
              Notes (Optional)
            </label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              rows={3}
              placeholder="Additional information about this account"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Active Status */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_active"
              name="is_active"
              checked={formData.is_active}
              onChange={handleChange}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="is_active" className="ml-2 text-sm text-gray-700">
              Account is active
            </label>
          </div>

          {/* Buttons */}
          <div className="flex space-x-3 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? 'Saving...' : account ? 'Update Account' : 'Add Account'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
