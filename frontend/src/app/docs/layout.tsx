'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Book, Home, Lightbulb, Settings, Code, ChevronDown, ChevronRight, Search } from 'lucide-react'

interface NavItem {
  title: string
  href: string
  icon?: any
  children?: NavItem[]
}

const navigation: NavItem[] = [
  {
    title: 'Overview',
    href: '/docs',
    icon: Home,
  },
  {
    title: 'Getting Started',
    href: '/docs/getting-started',
    icon: Book,
    children: [
      { title: 'Quick Start', href: '/docs/getting-started' },
      { title: 'Schwab OAuth Setup', href: '/docs/getting-started/schwab-oauth' },
      { title: 'Client Onboarding', href: '/docs/getting-started/client-onboarding' },
      { title: 'First Rebalance', href: '/docs/getting-started/first-rebalance' },
    ],
  },
  {
    title: 'Methodology',
    href: '/docs/methodology',
    icon: Lightbulb,
    children: [
      { title: 'Overview', href: '/docs/methodology' },
      { title: 'Trading Strategies', href: '/docs/methodology/trading-strategies' },
      { title: 'Hybrid ML+RL System', href: '/docs/methodology/hybrid-ml-rl' },
      { title: 'Risk Management', href: '/docs/methodology/risk-management' },
      { title: 'Market Regime Detection', href: '/docs/methodology/market-regime' },
    ],
  },
  {
    title: 'Operations',
    href: '/docs/operations',
    icon: Settings,
    children: [
      { title: 'Overview', href: '/docs/operations' },
      { title: 'Daily Operations', href: '/docs/operations/daily-operations' },
      { title: 'Model Retraining', href: '/docs/operations/model-retraining' },
      { title: 'Incremental Learning', href: '/docs/operations/incremental-learning' },
      { title: 'Rebalancing Process', href: '/docs/operations/rebalancing' },
      { title: 'Monitoring & Alerts', href: '/docs/operations/monitoring' },
      { title: 'Troubleshooting', href: '/docs/operations/troubleshooting' },
    ],
  },
  {
    title: 'Technical',
    href: '/docs/technical',
    icon: Code,
    children: [
      { title: 'Architecture', href: '/docs/technical' },
      { title: 'Database Schema', href: '/docs/technical/database' },
      { title: 'API Reference', href: '/docs/technical/api' },
      { title: 'ML Models', href: '/docs/technical/ml-models' },
      { title: 'RL Training', href: '/docs/technical/rl-training' },
      { title: 'Deployment', href: '/docs/technical/deployment' },
    ],
  },
]

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(navigation.map((item) => item.href))
  )
  const [searchQuery, setSearchQuery] = useState('')

  const toggleSection = (href: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(href)) {
      newExpanded.delete(href)
    } else {
      newExpanded.add(href)
    }
    setExpandedSections(newExpanded)
  }

  const isActive = (href: string) => {
    if (href === '/docs') {
      return pathname === href
    }
    return pathname?.startsWith(href)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-sm text-gray-600 hover:text-gray-900">
                ← Back to App
              </Link>
              <div className="h-6 w-px bg-gray-300" />
              <h1 className="text-xl font-semibold text-gray-900">ACIS AI Documentation</h1>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Sidebar */}
          <aside className="w-64 flex-shrink-0">
            <div className="sticky top-24">
              {/* Search */}
              <div className="mb-6">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search docs..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
              </div>

              {/* Navigation */}
              <nav className="space-y-1">
                {navigation.map((item) => {
                  const Icon = item.icon
                  const isExpanded = expandedSections.has(item.href)
                  const hasChildren = item.children && item.children.length > 0

                  return (
                    <div key={item.href}>
                      <div
                        className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                          isActive(item.href)
                            ? 'bg-blue-50 text-blue-700'
                            : 'text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <Link href={item.href} className="flex items-center gap-2 flex-1">
                          {Icon && <Icon className="w-4 h-4" />}
                          <span className="text-sm font-medium">{item.title}</span>
                        </Link>
                        {hasChildren && (
                          <button
                            onClick={(e) => {
                              e.preventDefault()
                              toggleSection(item.href)
                            }}
                            className="p-1 hover:bg-gray-200 rounded"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        )}
                      </div>

                      {/* Children */}
                      {hasChildren && isExpanded && (
                        <div className="ml-6 mt-1 space-y-1">
                          {item.children!.map((child) => (
                            <Link
                              key={child.href}
                              href={child.href}
                              className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                                isActive(child.href)
                                  ? 'bg-blue-50 text-blue-700 font-medium'
                                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                              }`}
                            >
                              {child.title}
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </nav>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 min-w-0">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}
