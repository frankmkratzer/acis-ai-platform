'use client'

import Link from 'next/link'
import { Book, Lightbulb, Settings, Code, TrendingUp, Shield, BarChart3, Zap } from 'lucide-react'

export default function DocsHome() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">ACIS AI Platform Documentation</h1>
      <p className="text-xl text-gray-600 mb-8">
        Complete guide to understanding, operating, and maintaining the ACIS AI autonomous trading platform.
      </p>

      {/* Executive Summary */}
      <div className="bg-blue-50 border-l-4 border-blue-600 p-6 mb-8 not-prose">
        <h2 className="text-xl font-semibold text-gray-900 mb-3">What is ACIS AI?</h2>
        <p className="text-gray-700 leading-relaxed mb-3">
          ACIS AI is a sophisticated autonomous investment platform that combines machine learning (ML) and
          reinforcement learning (RL) to manage client portfolios across multiple trading strategies and market
          capitalizations.
        </p>
        <p className="text-gray-700 leading-relaxed">
          The system automatically selects optimal strategies based on market conditions, rebalances portfolios,
          and executes trades through brokerage integrations (Schwab) while maintaining risk controls and
          compliance standards.
        </p>
      </div>

      {/* Key Features */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Key Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Hybrid ML+RL System</h3>
            </div>
            <p className="text-gray-600 text-sm">
              XGBoost models screen 2000+ stocks down to top 100 candidates. PPO reinforcement learning
              agents optimize portfolio allocation across top 50 positions.
            </p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <BarChart3 className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Multiple Strategies</h3>
            </div>
            <p className="text-gray-600 text-sm">
              4 trading strategies (Growth, Momentum, Value, Dividend) × 3 market caps (Large, Mid, Small)
              = 12 specialized portfolio models.
            </p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Zap className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Autonomous Operation</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Meta-model selects optimal strategy based on market regime. Daily rebalancing with
              threshold-based drift detection. Paper trading and live execution modes.
            </p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <Shield className="w-6 h-6 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Risk Management</h3>
            </div>
            <p className="text-gray-600 text-sm">
              Position limits, drift thresholds, minimum cash balance, transaction cost modeling.
              Tax-loss harvesting and compliance monitoring built-in.
            </p>
          </div>
        </div>
      </section>

      {/* Quick Navigation */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Documentation Sections</h2>
        <div className="grid grid-cols-1 gap-4 not-prose">
          <Link href="/docs/getting-started" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-blue-500 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-blue-100 rounded-lg group-hover:bg-blue-200 transition-colors">
                  <Book className="w-6 h-6 text-blue-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                    Getting Started
                  </h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Quick start guide, Schwab OAuth setup, client onboarding, and executing your first rebalance.
                  </p>
                  <span className="text-blue-600 text-sm font-medium">Start here →</span>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/docs/methodology" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-blue-500 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors">
                  <Lightbulb className="w-6 h-6 text-purple-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                    Methodology
                  </h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Trading strategies, hybrid ML+RL architecture, risk management, and market regime detection.
                  </p>
                  <span className="text-blue-600 text-sm font-medium">Learn how it works →</span>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/docs/operations" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-blue-500 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                  <Settings className="w-6 h-6 text-green-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                    Operations
                  </h3>
                  <p className="text-gray-600 text-sm mb-3">
                    Daily operations, model retraining, rebalancing process, monitoring, and troubleshooting.
                  </p>
                  <span className="text-blue-600 text-sm font-medium">Operate the platform →</span>
                </div>
              </div>
            </div>
          </Link>

          <Link href="/docs/technical" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-6 hover:border-blue-500 transition-colors">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-orange-100 rounded-lg group-hover:bg-orange-200 transition-colors">
                  <Code className="w-6 h-6 text-orange-600" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                    Technical Documentation
                  </h3>
                  <p className="text-gray-600 text-sm mb-3">
                    System architecture, database schema, API reference, ML models, RL training, and deployment.
                  </p>
                  <span className="text-blue-600 text-sm font-medium">View technical details →</span>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </section>

      {/* System Requirements */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">System Requirements</h2>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 not-prose">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Software Stack</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>• <strong>Backend:</strong> Python 3.11+, FastAPI, PostgreSQL</li>
                <li>• <strong>Frontend:</strong> Next.js 14, React, TypeScript</li>
                <li>• <strong>ML/RL:</strong> XGBoost, JAX, Gymnasium</li>
                <li>• <strong>Data:</strong> Alpha Vantage API, Schwab API</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Infrastructure</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>• <strong>Compute:</strong> NVIDIA GPU (CUDA 12.1+) for RL training</li>
                <li>• <strong>Database:</strong> PostgreSQL 14+ with 50GB+ storage</li>
                <li>• <strong>Network:</strong> ngrok for OAuth callbacks (optional)</li>
                <li>• <strong>OS:</strong> Linux (Ubuntu 20.04+ recommended)</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Support */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Need Help?</h2>
        <p className="text-gray-600 mb-4">
          If you encounter any issues or have questions not covered in this documentation:
        </p>
        <ul className="list-disc pl-6 space-y-2 text-gray-600">
          <li>Check the <Link href="/docs/operations/troubleshooting" className="text-blue-600 hover:underline">Troubleshooting Guide</Link></li>
          <li>Review the <Link href="/docs/technical/api" className="text-blue-600 hover:underline">API Reference</Link></li>
          <li>Consult the inline help (? icons) throughout the application</li>
        </ul>
      </section>
    </div>
  )
}
