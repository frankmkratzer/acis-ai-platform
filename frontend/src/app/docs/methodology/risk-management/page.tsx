'use client'
import Link from 'next/link'
import { Shield, AlertTriangle, TrendingDown } from 'lucide-react'

export default function RiskManagement() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Risk Management</h1>
      <p className="text-xl text-gray-600 mb-8">Position limits, drift thresholds, and automated risk controls.</p>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Position Limits</h2>
        <div className="grid grid-cols-3 gap-3 not-prose text-xs">
          <div className="bg-white border p-3 rounded text-center">
            <p className="font-bold text-sm">Max Per Stock</p>
            <p className="text-2xl font-bold text-blue-600">5%</p>
            <p className="text-gray-600 mt-1">Of total portfolio value</p>
          </div>
          <div className="bg-white border p-3 rounded text-center">
            <p className="font-bold text-sm">Min Positions</p>
            <p className="text-2xl font-bold text-green-600">40</p>
            <p className="text-gray-600 mt-1">Diversification requirement</p>
          </div>
          <div className="bg-white border p-3 rounded text-center">
            <p className="font-bold text-sm">Cash Reserve</p>
            <p className="text-2xl font-bold text-orange-600">5%</p>
            <p className="text-gray-600 mt-1">Minimum cash buffer</p>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Drift Management</h2>
        <p className="text-sm">Rebalancing triggered when portfolio drifts from target allocation:</p>
        <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs mt-3 not-prose">
          if drift {'>'} 15%: rebalance_immediately()<br/>
          if drift {'>'} 5%: schedule_rebalance(within_3_days)<br/>
          if drift {'<'} 5%: continue_monitoring()
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Risk Controls</h2>
        <div className="space-y-2 not-prose text-sm">
          <div className="bg-white border p-3 rounded">
            <strong>Stop Loss:</strong> Auto-exit if position drops 20% from entry
          </div>
          <div className="bg-white border p-3 rounded">
            <strong>Sector Limits:</strong> Max 30% exposure to single sector
          </div>
          <div className="bg-white border p-3 rounded">
            <strong>Volatility Filter:</strong> Exclude stocks with beta {'>'} 2.5
          </div>
        </div>
      </section>
    </div>
  )
}
