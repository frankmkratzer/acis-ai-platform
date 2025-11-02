'use client'

import Link from 'next/link'
import { TrendingUp, Zap, DollarSign, Percent, ArrowRight } from 'lucide-react'

export default function TradingStrategies() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Trading Strategies</h1>
      <p className="text-xl text-gray-600 mb-8">
        Deep dive into Growth, Momentum, Value, and Dividend strategies used by ACIS AI.
      </p>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Strategy Overview</h2>
        <p className="text-sm">Each strategy uses specialized ML models trained on historical data (2015-2023) and optimized for specific market conditions.</p>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Growth Strategy</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-4 not-prose">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-green-100 rounded">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <h3 className="font-semibold text-gray-900">High-Growth Potential Stocks</h3>
          </div>
          <p className="text-sm mb-3">Focuses on companies with strong revenue and earnings growth.</p>
          <div className="bg-gray-50 p-3 rounded text-xs">
            <p className="font-semibold mb-2">Key Features:</p>
            <ul className="space-y-1">
              <li>• Revenue growth rate ({'>'} 15% YoY)</li>
              <li>• EPS growth momentum</li>
              <li>• Price-to-earnings growth (PEG) ratio</li>
              <li>• Return on equity (ROE)</li>
            </ul>
          </div>
          <div className="mt-3 bg-blue-50 p-2 rounded text-xs">
            <strong>Best for:</strong> Bull markets, technology sectors, expansion phases
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Momentum Strategy</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-4 not-prose">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-purple-100 rounded">
              <Zap className="w-5 h-5 text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900">Strong Price Trends</h3>
          </div>
          <p className="text-sm mb-3">Capitalizes on stocks with strong upward price momentum.</p>
          <div className="bg-gray-50 p-3 rounded text-xs">
            <p className="font-semibold mb-2">Key Features:</p>
            <ul className="space-y-1">
              <li>• 3, 6, 12-month price performance</li>
              <li>• Relative strength index (RSI)</li>
              <li>• Moving average crossovers (50/200 day)</li>
              <li>• Volume-weighted momentum</li>
            </ul>
          </div>
          <div className="mt-3 bg-blue-50 p-2 rounded text-xs">
            <strong>Best for:</strong> Trending markets, sector rotations, positive sentiment
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Value Strategy</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-4 not-prose">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-100 rounded">
              <DollarSign className="w-5 h-5 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900">Undervalued Fundamentals</h3>
          </div>
          <p className="text-sm mb-3">Targets stocks trading below intrinsic value.</p>
          <div className="bg-gray-50 p-3 rounded text-xs">
            <p className="font-semibold mb-2">Key Features:</p>
            <ul className="space-y-1">
              <li>• Price-to-book (P/B) ratio</li>
              <li>• Price-to-earnings (P/E) ratio</li>
              <li>• Free cash flow yield</li>
              <li>• Debt-to-equity ratio</li>
            </ul>
          </div>
          <div className="mt-3 bg-blue-50 p-2 rounded text-xs">
            <strong>Best for:</strong> Market corrections, defensive positioning, recovery phases
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Dividend Strategy</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-4 not-prose">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-orange-100 rounded">
              <Percent className="w-5 h-5 text-orange-600" />
            </div>
            <h3 className="font-semibold text-gray-900">High Dividend Yield</h3>
          </div>
          <p className="text-sm mb-3">Focuses on stocks with consistent dividend payments.</p>
          <div className="bg-gray-50 p-3 rounded text-xs">
            <p className="font-semibold mb-2">Key Features:</p>
            <ul className="space-y-1">
              <li>• Dividend yield ({'>'} 2.5%)</li>
              <li>• Dividend growth history</li>
              <li>• Payout ratio sustainability</li>
              <li>• Cash flow stability</li>
            </ul>
          </div>
          <div className="mt-3 bg-blue-50 p-2 rounded text-xs">
            <strong>Best for:</strong> Income generation, low volatility, bear markets
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Market Cap Segments</h2>
        <div className="grid grid-cols-3 gap-3 not-prose text-xs">
          <div className="bg-gray-50 border p-3 rounded text-center">
            <p className="font-bold text-sm mb-1">Large Cap</p>
            <p className="text-gray-600">{'>'} $10B</p>
            <p className="mt-2 text-xs">Lower risk, stable returns</p>
          </div>
          <div className="bg-gray-50 border p-3 rounded text-center">
            <p className="font-bold text-sm mb-1">Mid Cap</p>
            <p className="text-gray-600">$2B - $10B</p>
            <p className="mt-2 text-xs">Balanced risk-reward</p>
          </div>
          <div className="bg-gray-50 border p-3 rounded text-center">
            <p className="font-bold text-sm mb-1">Small Cap</p>
            <p className="text-gray-600">{'<'} $2B</p>
            <p className="mt-2 text-xs">Higher risk, growth potential</p>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Related Documentation</h2>
        <div className="grid grid-cols-2 gap-3 not-prose">
          <Link href="/docs/methodology/hybrid-ml-rl" className="block p-3 bg-white border-2 border-gray-200 rounded hover:border-blue-500">
            <h3 className="font-semibold text-sm">Hybrid ML+RL System</h3>
            <p className="text-xs text-gray-600">How strategies are implemented</p>
          </Link>
          <Link href="/docs/methodology/market-regime" className="block p-3 bg-white border-2 border-gray-200 rounded hover:border-blue-500">
            <h3 className="font-semibold text-sm">Market Regime Detection</h3>
            <p className="text-xs text-gray-600">Auto strategy selection</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
