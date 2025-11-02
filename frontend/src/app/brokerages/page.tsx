'use client'

import { useState, useEffect } from 'react'
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

export default function BrokeragesPage() {
  const [brokerages, setBrokerages] = useState<Brokerage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    loadBrokerages()
  }, [])

  const loadBrokerages = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/api/brokerages/')
      setBrokerages(response.data)
    } catch (error: any) {
      console.error('Failed to load brokerages:', error)
      setError(error.response?.data?.detail || 'Failed to load brokerages')
    } finally {
      setLoading(false)
    }
  }

  const handleModalSave = () => {
    loadBrokerages()
  }

  return (
    <div className="p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Brokerages</h1>
            <p className="mt-2 text-gray-600">Manage brokerage integrations and OAuth connections</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Add Brokerage
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <p className="mt-2 text-gray-600">Loading brokerages...</p>
          </div>
        )}

        {/* Brokerages Grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {brokerages.map((brokerage) => (
              <Link
                key={brokerage.brokerage_id}
                href={`/brokerages/${brokerage.brokerage_id}`}
                className="block"
              >
                <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 p-6 h-full border-2 border-transparent hover:border-blue-500">
                  {/* Brokerage Name */}
                  <div className="mb-4">
                    <h2 className="text-xl font-bold text-gray-900">
                      {brokerage.display_name || brokerage.name}
                    </h2>
                    {brokerage.display_name && (
                      <p className="text-sm text-gray-500">{brokerage.name}</p>
                    )}
                  </div>

                  {/* Status Badge */}
                  <div className="mb-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      brokerage.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {brokerage.status}
                    </span>
                  </div>

                  {/* Features */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Live Trading:</span>
                      <span className={`font-medium ${
                        brokerage.supports_live_trading ? 'text-green-600' : 'text-gray-400'
                      }`}>
                        {brokerage.supports_live_trading ? 'Yes' : 'No'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Paper Trading:</span>
                      <span className={`font-medium ${
                        brokerage.supports_paper_trading ? 'text-green-600' : 'text-gray-400'
                      }`}>
                        {brokerage.supports_paper_trading ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {brokerage.api_type && (
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">API Type:</span>
                        <span className="font-medium text-gray-900">{brokerage.api_type}</span>
                      </div>
                    )}
                  </div>

                  {/* View Details Link */}
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <span className="text-blue-600 text-sm font-medium hover:text-blue-700">
                      View Details & Manage OAuth →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && brokerages.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg shadow-md">
            <p className="text-gray-500 text-lg">No brokerages found</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Add Your First Brokerage
            </button>
          </div>
        )}

        {/* Modal */}
        <BrokerageFormModal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          onSave={handleModalSave}
        />
      </div>
    </div>
  )
}
