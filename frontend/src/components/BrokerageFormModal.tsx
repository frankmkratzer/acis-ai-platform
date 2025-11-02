'use client'

import { useState, useEffect } from 'react'

interface Brokerage {
  brokerage_id?: number
  name: string
  display_name: string
  supports_live_trading: boolean
  supports_paper_trading: boolean
  api_type?: string
  status?: string
}

interface BrokerageFormModalProps {
  isOpen: boolean
  onClose: () => void
  brokerage?: Brokerage | null
  onSave: () => void
}

export default function BrokerageFormModal({
  isOpen,
  onClose,
  brokerage,
  onSave,
}: BrokerageFormModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    supports_live_trading: true,
    supports_paper_trading: false,
    api_type: 'rest',
    status: 'active',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      if (brokerage) {
        // Editing existing brokerage
        setFormData({
          name: brokerage.name,
          display_name: brokerage.display_name,
          supports_live_trading: brokerage.supports_live_trading,
          supports_paper_trading: brokerage.supports_paper_trading,
          api_type: brokerage.api_type || 'rest',
          status: brokerage.status || 'active',
        })
      } else {
        // Creating new brokerage
        setFormData({
          name: '',
          display_name: '',
          supports_live_trading: true,
          supports_paper_trading: false,
          api_type: 'rest',
          status: 'active',
        })
      }
      setError(null)
    }
  }, [isOpen, brokerage])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      const url = brokerage
        ? `http://localhost:8000/api/brokerages/${brokerage.brokerage_id}`
        : 'http://localhost:8000/api/brokerages/'

      const method = brokerage ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to save brokerage')
      }

      onSave()
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to save brokerage')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div
          className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75"
          onClick={onClose}
        />

        {/* Modal panel */}
        <div className="inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
          <div className="absolute top-0 right-0 pt-4 pr-4">
            <button
              type="button"
              className="bg-white rounded-md text-gray-400 hover:text-gray-500"
              onClick={onClose}
            >
              <span className="sr-only">Close</span>
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="sm:flex sm:items-start">
            <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                {brokerage ? 'Edit Brokerage' : 'Add New Brokerage'}
              </h3>

              <form onSubmit={handleSubmit} className="mt-5">
                <div className="space-y-4">
                  {/* Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      placeholder="schwab"
                      required
                      disabled={submitting}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Lowercase identifier (e.g., schwab, tdameritrade, interactivebrokers)
                    </p>
                  </div>

                  {/* Display Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Display Name *
                    </label>
                    <input
                      type="text"
                      value={formData.display_name}
                      onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      placeholder="Charles Schwab"
                      required
                      disabled={submitting}
                    />
                  </div>

                  {/* API Type */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      API Type
                    </label>
                    <select
                      value={formData.api_type}
                      onChange={(e) => setFormData({ ...formData, api_type: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={submitting}
                    >
                      <option value="rest">REST</option>
                      <option value="websocket">WebSocket</option>
                      <option value="fix">FIX</option>
                    </select>
                  </div>

                  {/* Checkboxes */}
                  <div className="space-y-2">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="supports_live_trading"
                        checked={formData.supports_live_trading}
                        onChange={(e) =>
                          setFormData({ ...formData, supports_live_trading: e.target.checked })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        disabled={submitting}
                      />
                      <label htmlFor="supports_live_trading" className="ml-2 block text-sm text-gray-700">
                        Supports Live Trading
                      </label>
                    </div>

                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="supports_paper_trading"
                        checked={formData.supports_paper_trading}
                        onChange={(e) =>
                          setFormData({ ...formData, supports_paper_trading: e.target.checked })
                        }
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        disabled={submitting}
                      />
                      <label htmlFor="supports_paper_trading" className="ml-2 block text-sm text-gray-700">
                        Supports Paper Trading
                      </label>
                    </div>
                  </div>

                  {/* Status */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Status
                    </label>
                    <select
                      value={formData.status}
                      onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      disabled={submitting}
                    >
                      <option value="active">Active</option>
                      <option value="inactive">Inactive</option>
                      <option value="deprecated">Deprecated</option>
                    </select>
                  </div>

                  {/* Error Message */}
                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="mt-5 sm:mt-6 sm:grid sm:grid-cols-2 sm:gap-3 sm:grid-flow-row-dense">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:col-start-2 sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? 'Saving...' : brokerage ? 'Update Brokerage' : 'Add Brokerage'}
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    disabled={submitting}
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:col-start-1 sm:text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
