'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ChevronDown } from 'lucide-react'

export default function NavigationBar() {
  const [tradingMenuOpen, setTradingMenuOpen] = useState(false)
  const [aiModelsMenuOpen, setAiModelsMenuOpen] = useState(false)

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            {/* Logo */}
            <Link href="/" className="flex items-center">
              <span className="text-2xl font-bold text-blue-600">ACIS AI</span>
            </Link>

            {/* Navigation Links */}
            <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
              <Link
                href="/"
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 border-b-2 border-transparent hover:border-blue-500 transition-colors"
              >
                Dashboard
              </Link>
              <Link
                href="/autonomous"
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors"
              >
                Autonomous
              </Link>
              <Link
                href="/clients"
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors"
              >
                Clients
              </Link>
              <Link
                href="/brokerages"
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors"
              >
                Brokerages
              </Link>

              {/* Trading Dropdown */}
              <div className="relative" onMouseLeave={() => setTradingMenuOpen(false)}>
                <button
                  onClick={() => setTradingMenuOpen(!tradingMenuOpen)}
                  onMouseEnter={() => setTradingMenuOpen(true)}
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors gap-1 h-16"
                >
                  Trading
                  <ChevronDown className={`w-4 h-4 transition-transform ${tradingMenuOpen ? 'rotate-180' : ''}`} />
                </button>
                {tradingMenuOpen && (
                  <div className="absolute left-0 top-full w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-[100]">
                    <div className="py-1">
                      <Link
                        href="/trading"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setTradingMenuOpen(false)}
                      >
                        Trade Recommendations
                      </Link>
                      <Link
                        href="/trading/history"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setTradingMenuOpen(false)}
                      >
                        Trade History
                      </Link>
                      <Link
                        href="/test-live-trading"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setTradingMenuOpen(false)}
                      >
                        Test Live Trading
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              {/* AI & Models Dropdown */}
              <div className="relative" onMouseLeave={() => setAiModelsMenuOpen(false)}>
                <button
                  onClick={() => setAiModelsMenuOpen(!aiModelsMenuOpen)}
                  onMouseEnter={() => setAiModelsMenuOpen(true)}
                  className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors gap-1 h-16"
                >
                  AI & Models
                  <ChevronDown className={`w-4 h-4 transition-transform ${aiModelsMenuOpen ? 'rotate-180' : ''}`} />
                </button>
                {aiModelsMenuOpen && (
                  <div className="absolute left-0 top-full w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-[100]">
                    <div className="py-1">
                      <Link
                        href="/ml-portfolio"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setAiModelsMenuOpen(false)}
                      >
                        Portfolio Generator
                      </Link>
                      <Link
                        href="/ml-models"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setAiModelsMenuOpen(false)}
                      >
                        Model Management
                      </Link>
                      <Link
                        href="/backtest"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setAiModelsMenuOpen(false)}
                      >
                        Backtesting
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              <Link
                href="/docs"
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors"
              >
                Documentation
              </Link>
              <Link
                href="/admin"
                className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-500 border-b-2 border-transparent hover:text-gray-900 hover:border-blue-500 transition-colors"
              >
                System Admin
              </Link>
            </div>
          </div>

          {/* User Info */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-blue-100 text-blue-800">
                Admin
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="sm:hidden">
        <div className="pt-2 pb-3 space-y-1">
          <Link
            href="/"
            className="block pl-3 pr-4 py-2 text-base font-medium text-gray-900 bg-blue-50 border-l-4 border-blue-500"
          >
            Dashboard
          </Link>
          <Link
            href="/autonomous"
            className="block pl-3 pr-4 py-2 text-base font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 hover:border-gray-300 border-l-4 border-transparent"
          >
            Autonomous
          </Link>
          <Link
            href="/clients"
            className="block pl-3 pr-4 py-2 text-base font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 hover:border-gray-300 border-l-4 border-transparent"
          >
            Clients
          </Link>
          <Link
            href="/brokerages"
            className="block pl-3 pr-4 py-2 text-base font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 hover:border-gray-300 border-l-4 border-transparent"
          >
            Brokerages
          </Link>

          {/* Trading Section */}
          <div className="pl-3 pr-4 py-2 text-base font-medium text-gray-700 border-l-4 border-transparent">
            Trading
          </div>
          <Link
            href="/trading"
            className="block pl-6 pr-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50"
          >
            Trade Recommendations
          </Link>
          <Link
            href="/trading/history"
            className="block pl-6 pr-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50"
          >
            Trade History
          </Link>
          <Link
            href="/test-live-trading"
            className="block pl-6 pr-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50"
          >
            Test Live Trading
          </Link>

          {/* AI & Models Section */}
          <div className="pl-3 pr-4 py-2 text-base font-medium text-gray-700 border-l-4 border-transparent">
            AI & Models
          </div>
          <Link
            href="/ml-portfolio"
            className="block pl-6 pr-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50"
          >
            Portfolio Generator
          </Link>
          <Link
            href="/ml-models"
            className="block pl-6 pr-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50"
          >
            Model Management
          </Link>
          <Link
            href="/backtest"
            className="block pl-6 pr-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50"
          >
            Backtesting
          </Link>

          {/* Documentation */}
          <Link
            href="/docs"
            className="block pl-3 pr-4 py-2 text-base font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 hover:border-gray-300 border-l-4 border-transparent"
          >
            Documentation
          </Link>

          {/* System Admin */}
          <Link
            href="/admin"
            className="block pl-3 pr-4 py-2 text-base font-medium text-gray-500 hover:text-gray-900 hover:bg-gray-50 hover:border-gray-300 border-l-4 border-transparent"
          >
            System Admin
          </Link>
        </div>
      </div>
    </nav>
  )
}
