'use client'

import { useState, useEffect } from 'react'
import type { BrokerageAccount } from '@/types'

interface TradeModalProps {
  isOpen: boolean
  onClose: () => void
  symbol: string
  currentQuantity?: number
  currentPrice?: number
  accountHash: string
  clientId: number
  tradeType: 'BUY' | 'SELL'
  onSuccess?: () => void
}

export default function TradeModal({
  isOpen,
  onClose,
  symbol,
  currentQuantity = 0,
  currentPrice = 0,
  accountHash,
  clientId,
  tradeType,
  onSuccess,
}: TradeModalProps) {
  const [quantity, setQuantity] = useState<number>(1)
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET')
  const [limitPrice, setLimitPrice] = useState<string>('')
  const [timeInForce, setTimeInForce] = useState<'DAY' | 'GTC'>('DAY')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isOpen) {
      // Reset form when modal opens
      setQuantity(tradeType === 'SELL' ? Math.min(10, currentQuantity) : 10)
      setOrderType('MARKET')
      setLimitPrice(currentPrice > 0 ? currentPrice.toFixed(2) : '')
      setTimeInForce('DAY')
      setError(null)
    }
  }, [isOpen, tradeType, currentQuantity, currentPrice])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validate quantity
    if (quantity <= 0) {
      setError('Quantity must be greater than 0')
      return
    }

    if (tradeType === 'SELL' && quantity > currentQuantity) {
      setError(`Cannot sell more than ${currentQuantity} shares`)
      return
    }

    // Validate limit price
    if (orderType === 'LIMIT') {
      const price = parseFloat(limitPrice)
      if (isNaN(price) || price <= 0) {
        setError('Please enter a valid limit price')
        return
      }
    }

    try {
      setSubmitting(true)
      setError(null)

      // Build order object (matching Schwab API format)
      const order = {
        orderType,
        session: 'NORMAL',
        duration: timeInForce,
        orderStrategyType: 'SINGLE',
        orderLegCollection: [
          {
            instruction: tradeType === 'BUY' ? 'BUY' : 'SELL',
            quantity: quantity,
            instrument: {
              symbol: symbol,
              assetType: 'EQUITY',
            },
          },
        ],
      }

      // Add price for limit orders
      if (orderType === 'LIMIT') {
        ;(order as any).price = parseFloat(limitPrice)
      }

      // Submit order via API
      const response = await fetch(
        `http://localhost:8000/api/schwab/orders/${accountHash}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(order),
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to place order')
      }

      const result = await response.json()

      // Success!
      if (onSuccess) {
        onSuccess()
      }

      onClose()
    } catch (err: any) {
      console.error('Failed to place order:', err)
      setError(err.message || 'Failed to place order')
    } finally {
      setSubmitting(false)
    }
  }

  const estimatedTotal = orderType === 'MARKET'
    ? currentPrice * quantity
    : parseFloat(limitPrice || '0') * quantity

  const maxSellQuantity = currentQuantity

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
            <div
              className={`mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full sm:mx-0 sm:h-10 sm:w-10 ${
                tradeType === 'BUY' ? 'bg-green-100' : 'bg-red-100'
              }`}
            >
              {tradeType === 'BUY' ? (
                <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              ) : (
                <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              )}
            </div>
            <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left flex-1">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                {tradeType} {symbol}
              </h3>
              <div className="mt-2">
                <p className="text-sm text-gray-500">
                  {tradeType === 'SELL' && (
                    <>Current position: {currentQuantity} shares | </>
                  )}
                  Current price: ${currentPrice.toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="mt-5">
            <div className="space-y-4">
              {/* Order Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Order Type
                </label>
                <select
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value as 'MARKET' | 'LIMIT')}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  disabled={submitting}
                >
                  <option value="MARKET">Market Order</option>
                  <option value="LIMIT">Limit Order</option>
                </select>
              </div>

              {/* Quantity */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Quantity
                  {tradeType === 'SELL' && (
                    <span className="text-gray-500 font-normal ml-2">
                      (Max: {maxSellQuantity})
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  min="1"
                  max={tradeType === 'SELL' ? maxSellQuantity : undefined}
                  value={quantity}
                  onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  disabled={submitting}
                  required
                />
              </div>

              {/* Limit Price (only for limit orders) */}
              {orderType === 'LIMIT' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Limit Price
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <span className="text-gray-500 sm:text-sm">$</span>
                    </div>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={limitPrice}
                      onChange={(e) => setLimitPrice(e.target.value)}
                      className="block w-full pl-7 pr-12 rounded-md border-gray-300 focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                      placeholder="0.00"
                      disabled={submitting}
                      required
                    />
                  </div>
                </div>
              )}

              {/* Time in Force */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Time in Force
                </label>
                <select
                  value={timeInForce}
                  onChange={(e) => setTimeInForce(e.target.value as 'DAY' | 'GTC')}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                  disabled={submitting}
                >
                  <option value="DAY">Day (Cancel at end of day)</option>
                  <option value="GTC">Good Till Cancel</option>
                </select>
              </div>

              {/* Order Summary */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Estimated Total:</span>
                  <span className="font-medium text-gray-900">
                    ${estimatedTotal.toFixed(2)}
                  </span>
                </div>
                {orderType === 'MARKET' && (
                  <p className="text-xs text-gray-500">
                    Market orders execute at current market price
                  </p>
                )}
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
                className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 sm:col-start-2 sm:text-sm ${
                  tradeType === 'BUY'
                    ? 'bg-green-600 hover:bg-green-700 focus:ring-green-500'
                    : 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
                } ${submitting ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {submitting ? 'Placing Order...' : `${tradeType} ${symbol}`}
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
  )
}
