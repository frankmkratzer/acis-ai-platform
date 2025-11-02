'use client'

import Link from 'next/link'
import { AlertCircle, CheckCircle, ArrowRight } from 'lucide-react'

export default function GettingStarted() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Getting Started</h1>
      <p className="text-xl text-gray-600 mb-8">
        Quick start guide to get ACIS AI Platform up and running.
      </p>

      {/* Prerequisites */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Prerequisites</h2>
        <div className="bg-yellow-50 border-l-4 border-yellow-600 p-4 not-prose mb-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-900 mb-1">Important: Read Before Starting</p>
              <p className="text-sm text-yellow-800">
                Ensure you have all prerequisites installed and configured before proceeding.
              </p>
            </div>
          </div>
        </div>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">Required Software</h3>
        <ul className="space-y-2 mb-6">
          <li><strong>Python 3.11+</strong> - Backend runtime environment</li>
          <li><strong>Node.js 18+</strong> - Frontend runtime environment</li>
          <li><strong>PostgreSQL 14+</strong> - Database system</li>
          <li><strong>NVIDIA GPU</strong> - For RL training (CUDA 12.1+ compatible)</li>
          <li><strong>ngrok</strong> - For Schwab OAuth callbacks (optional but recommended)</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">Required API Keys</h3>
        <ul className="space-y-2 mb-6">
          <li><strong>Alpha Vantage API Key</strong> - For market data (free tier available)</li>
          <li><strong>Schwab Developer Account</strong> - For brokerage integration</li>
        </ul>
      </section>

      {/* Installation */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Installation</h2>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">1. Clone Repository</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          git clone https://github.com/youraccount/acis-ai-platform.git<br/>
          cd acis-ai-platform
        </div>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">2. Set Up Python Environment</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          python -m venv venv<br/>
          source venv/bin/activate  # On Windows: venv\Scripts\activate<br/>
          pip install -r requirements.txt
        </div>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">3. Configure Database</h3>
        <p className="mb-4">Create PostgreSQL database and initialize schema:</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          PGPASSWORD='your_password' psql -U postgres -c "CREATE DATABASE acis_ai;"<br/>
          PGPASSWORD='your_password' psql -U postgres -d acis_ai -f database/schema.sql<br/>
          PGPASSWORD='your_password' psql -U postgres -d acis_ai -f database/initial_data.sql
        </div>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">4. Configure Environment Variables</h3>
        <p className="mb-4">Create <code>.env</code> file in backend directory:</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          # Database<br/>
          DATABASE_URL=postgresql://postgres:password@localhost/acis_ai<br/>
          <br/>
          # Alpha Vantage<br/>
          ALPHA_VANTAGE_API_KEY=your_api_key_here<br/>
          <br/>
          # Schwab OAuth<br/>
          SCHWAB_CLIENT_ID=your_client_id<br/>
          SCHWAB_CLIENT_SECRET=your_client_secret<br/>
          SCHWAB_REDIRECT_URI=https://your-ngrok-url.ngrok.io/api/schwab/callback
        </div>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">5. Install Frontend Dependencies</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          cd frontend<br/>
          npm install<br/>
          cd ..
        </div>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">6. Initial Data Load</h3>
        <p className="mb-4">Load initial market data (this may take 30-60 minutes):</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          source venv/bin/activate<br/>
          python scripts/run_eod_pipeline.sh
        </div>
      </section>

      {/* Running the Platform */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Running the Platform</h2>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">Start Backend Server</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          cd backend<br/>
          source ../venv/bin/activate<br/>
          uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
        </div>
        <p className="text-sm text-gray-600 mb-6">Backend will be available at <code>http://localhost:8000</code></p>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">Start Frontend Development Server</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          cd frontend<br/>
          npm run dev
        </div>
        <p className="text-sm text-gray-600 mb-6">Frontend will be available at <code>http://localhost:3000</code></p>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">Start ngrok (for Schwab OAuth)</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          ngrok http 8000
        </div>
        <p className="text-sm text-gray-600 mb-6">
          Copy the ngrok HTTPS URL and update your <code>SCHWAB_REDIRECT_URI</code> environment variable and
          Schwab developer app settings.
        </p>
      </section>

      {/* Initial Setup Checklist */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Initial Setup Checklist</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose">
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-gray-700">
                <strong>Database initialized</strong> - Schema and initial data loaded
              </span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-gray-700">
                <strong>Backend running</strong> - API accessible at localhost:8000
              </span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-gray-700">
                <strong>Frontend running</strong> - UI accessible at localhost:3000
              </span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-gray-700">
                <strong>ngrok running</strong> - Callback URL configured in Schwab developer portal
              </span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <span className="text-sm text-gray-700">
                <strong>Market data loaded</strong> - Initial EOD pipeline completed
              </span>
            </li>
          </ul>
        </div>
      </section>

      {/* Next Steps */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Next Steps</h2>
        <p className="mb-6">Now that your platform is running, proceed with these guides:</p>

        <div className="grid grid-cols-1 gap-4 not-prose">
          <Link href="/docs/getting-started/schwab-oauth" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-4 hover:border-blue-500 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                    1. Configure Schwab OAuth
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Set up brokerage integration and authenticate client accounts
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
              </div>
            </div>
          </Link>

          <Link href="/docs/getting-started/client-onboarding" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-4 hover:border-blue-500 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                    2. Onboard Your First Client
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Create client profile and link brokerage account
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
              </div>
            </div>
          </Link>

          <Link href="/docs/getting-started/first-rebalance" className="group block">
            <div className="bg-white border-2 border-gray-200 rounded-lg p-4 hover:border-blue-500 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                    3. Execute Your First Rebalance
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Run autonomous portfolio rebalancing and review recommendations
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
              </div>
            </div>
          </Link>
        </div>
      </section>
    </div>
  )
}
