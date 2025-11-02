'use client'

import Link from 'next/link'
import { Play, TrendingUp, CheckCircle2, ArrowRight, AlertCircle } from 'lucide-react'

export default function FirstRebalance() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">First Rebalance</h1>
      <p className="text-xl text-gray-600 mb-8">
        Execute your first portfolio rebalance - from signal generation to trade execution.
      </p>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Workflow Overview</h2>
        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose text-sm">
          <ol className="space-y-2 text-blue-900">
            <li>1. ML model screens 2000+ stocks → Top 100 candidates</li>
            <li>2. RL agent optimizes allocation → Top 50 positions</li>
            <li>3. Calculate drift from current holdings</li>
            <li>4. Generate buy/sell recommendations</li>
            <li>5. Execute trades via Schwab API</li>
          </ol>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 1: Generate Recommendations</h2>
        <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs not-prose">
          curl -X POST http://localhost:8000/api/trading/recommendations \<br/>
          &nbsp;&nbsp;-d &apos;&#123;&quot;client_id&quot;: 1, &quot;strategy&quot;: &quot;growth&quot;, &quot;market_cap_segment&quot;: &quot;mid&quot;&#125;&apos;
        </div>
        <p className="text-sm mt-3">Or use the Trading page UI. Duration: ~30-60 seconds.</p>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 2: Review Recommendations</h2>
        <p className="text-sm">The system displays buy/sell orders with:</p>
        <div className="grid grid-cols-2 gap-3 mt-3 not-prose text-xs">
          <div className="bg-gray-50 p-3 rounded">
            <p className="font-semibold mb-1">Buy Orders:</p>
            <p>Ticker, quantity, price, total cost</p>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <p className="font-semibold mb-1">Sell Orders:</p>
            <p>Ticker, quantity, price, proceeds</p>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 3: Understanding Drift</h2>
        <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs not-prose">
          Drift = Σ |current_weight - target_weight| / 2
        </div>
        <div className="grid grid-cols-3 gap-2 mt-3 not-prose text-xs">
          <div className="bg-green-50 p-2 rounded text-center">
            <p className="font-bold">{'<'} 5%</p>
            <p className="text-green-700">No rebalance</p>
          </div>
          <div className="bg-yellow-50 p-2 rounded text-center">
            <p className="font-bold">5-15%</p>
            <p className="text-yellow-700">Consider</p>
          </div>
          <div className="bg-red-50 p-2 rounded text-center">
            <p className="font-bold">{'>'} 15%</p>
            <p className="text-red-700">Recommended</p>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 4: Execute Trades</h2>
        <div className="bg-blue-50 p-4 rounded not-prose text-sm mb-3">
          <p className="font-semibold mb-2">Execution Modes:</p>
          <p><strong>Paper Trading:</strong> Simulates trades (default for testing)</p>
          <p><strong>Live Trading:</strong> Real orders via Schwab API</p>
        </div>
        <p className="text-sm">Orders execute during market hours (9:30 AM - 4:00 PM ET). Sells execute first, then buys.</p>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Best Practices</h2>
        <div className="space-y-2 not-prose text-sm">
          <div className="bg-white border p-3 rounded">
            <p className="font-semibold">Start with Paper Trading</p>
            <p className="text-gray-600 text-xs">Test workflow before live execution</p>
          </div>
          <div className="bg-white border p-3 rounded">
            <p className="font-semibold">Verify Cash Balance</p>
            <p className="text-gray-600 text-xs">Ensure 5% minimum cash reserve</p>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Next Steps</h2>
        <div className="grid grid-cols-2 gap-3 not-prose">
          <Link href="/docs/operations/rebalancing" className="block p-3 bg-white border-2 border-gray-200 rounded hover:border-blue-500">
            <h3 className="font-semibold text-sm">Rebalancing Process</h3>
            <p className="text-xs text-gray-600">Detailed documentation</p>
          </Link>
          <Link href="/docs/operations/monitoring" className="block p-3 bg-white border-2 border-gray-200 rounded hover:border-blue-500">
            <h3 className="font-semibold text-sm">Monitoring & Alerts</h3>
            <p className="text-xs text-gray-600">Track performance</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
