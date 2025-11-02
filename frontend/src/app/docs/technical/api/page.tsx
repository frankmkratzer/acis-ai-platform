'use client'

import Link from 'next/link'
import { Code, ExternalLink } from 'lucide-react'

export default function ApiReference() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">API Reference</h1>
      <p className="text-xl text-gray-600 mb-8">
        Complete API documentation for the ACIS AI Platform backend.
      </p>

      {/* FastAPI Docs Link */}
      <div className="bg-blue-50 border-l-4 border-blue-600 p-6 mb-8 not-prose">
        <div className="flex items-start gap-3">
          <ExternalLink className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Interactive API Documentation</h2>
            <p className="text-gray-700 mb-4">
              The ACIS AI Platform uses FastAPI, which provides automatic interactive API documentation.
              Access the live, interactive docs for testing and exploring all endpoints:
            </p>
            <div className="space-y-2">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Swagger UI (Recommended)
                <ExternalLink className="w-4 h-4" />
              </a>
              <span className="mx-3 text-gray-400">or</span>
              <a
                href="http://localhost:8000/redoc"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
              >
                ReDoc
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Overview */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">API Overview</h2>
        <p>The ACIS AI Platform API is organized into the following sections:</p>

        <div className="grid grid-cols-1 gap-4 not-prose mt-6">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Clients & Accounts</h3>
            <p className="text-gray-600 text-sm mb-3">
              Manage client profiles, brokerage accounts, and OAuth connections.
            </p>
            <code className="text-sm text-blue-600">/api/clients/*</code>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Autonomous Trading</h3>
            <p className="text-gray-600 text-sm mb-3">
              Autonomous fund operations, portfolio rebalancing, and trade execution.
            </p>
            <code className="text-sm text-blue-600">/api/autonomous/*</code>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">ML Models</h3>
            <p className="text-gray-600 text-sm mb-3">
              XGBoost model training, inference, and management. Track training jobs and model metadata.
            </p>
            <code className="text-sm text-blue-600">/api/ml-models/*</code>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">RL Agents</h3>
            <p className="text-gray-600 text-sm mb-3">
              PPO reinforcement learning agent training and portfolio generation.
            </p>
            <code className="text-sm text-blue-600">/api/rl-portfolio/*</code>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Trading</h3>
            <p className="text-gray-600 text-sm mb-3">
              Generate trade recommendations, execute orders, and view trading history.
            </p>
            <code className="text-sm text-blue-600">/api/trading/*</code>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">System Admin</h3>
            <p className="text-gray-600 text-sm mb-3">
              System health, logs, pipeline triggers, and monitoring.
            </p>
            <code className="text-sm text-blue-600">/api/system/*</code>
          </div>
        </div>
      </section>

      {/* Authentication */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Authentication</h2>
        <p>The API currently does not require authentication for internal use. In production:</p>
        <ul>
          <li>Add API key authentication for external access</li>
          <li>Use OAuth 2.0 for client-specific operations</li>
          <li>Implement rate limiting and IP whitelisting</li>
        </ul>
      </section>

      {/* Common Patterns */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Common Patterns</h2>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Response Format</h3>
        <p>All API responses follow a consistent JSON format:</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm not-prose mb-6">
          {'{'}<br/>
          &nbsp;&nbsp;"status": "success",<br/>
          &nbsp;&nbsp;"data": {'{ ... }'},<br/>
          &nbsp;&nbsp;"message": "Optional message"<br/>
          {'}'}
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Error Handling</h3>
        <p>Errors return appropriate HTTP status codes with descriptive messages:</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm not-prose">
          {'{'}<br/>
          &nbsp;&nbsp;"detail": "Error description",<br/>
          &nbsp;&nbsp;"status_code": 400<br/>
          {'}'}
        </div>
      </section>

      {/* Example Endpoints */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Example Endpoints</h2>

        <div className="space-y-6 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">GET</span>
              <code className="text-sm">/api/clients</code>
            </div>
            <p className="text-gray-700 text-sm mb-2">List all clients with their accounts and balances.</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-semibold">POST</span>
              <code className="text-sm">/api/ml-models/train</code>
            </div>
            <p className="text-gray-700 text-sm mb-2">Start training a new ML model.</p>
            <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs mt-3">
              {'{'}<br/>
              &nbsp;&nbsp;"strategy": "growth",<br/>
              &nbsp;&nbsp;"market_cap_segment": "mid",<br/>
              &nbsp;&nbsp;"framework": "xgboost",<br/>
              &nbsp;&nbsp;"mode": "incremental"<br/>
              {'}'}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">GET</span>
              <code className="text-sm">/api/autonomous/status</code>
            </div>
            <p className="text-gray-700 text-sm mb-2">Get autonomous trading system status including current strategy, portfolio value, and recent trades.</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-semibold">POST</span>
              <code className="text-sm">/api/trading/recommendations</code>
            </div>
            <p className="text-gray-700 text-sm mb-2">Generate trade recommendations for a client's portfolio.</p>
            <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs mt-3">
              {'{'}<br/>
              &nbsp;&nbsp;"client_id": 1,<br/>
              &nbsp;&nbsp;"strategy": "growth",<br/>
              &nbsp;&nbsp;"market_cap_segment": "mid"<br/>
              {'}'}
            </div>
          </div>
        </div>
      </section>

      {/* Related */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Related Documentation</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
          <Link href="/docs/technical" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Technical Overview</h3>
            <p className="text-sm text-gray-600">System architecture and design</p>
          </Link>
          <Link href="/docs/operations" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Operations Manual</h3>
            <p className="text-sm text-gray-600">Daily operational procedures</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
