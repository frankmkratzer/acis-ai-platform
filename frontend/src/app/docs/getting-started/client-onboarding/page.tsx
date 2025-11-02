'use client'

import Link from 'next/link'
import { UserPlus, Key, Building2, CheckCircle2, ArrowRight, AlertTriangle } from 'lucide-react'

export default function ClientOnboarding() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Client Onboarding</h1>
      <p className="text-xl text-gray-600 mb-8">
        Step-by-step guide to adding new clients to the ACIS AI platform and connecting their brokerage accounts.
      </p>

      {/* Prerequisites */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Prerequisites</h2>
        <div className="bg-blue-50 border-l-4 border-blue-600 p-6 not-prose">
          <p className="text-blue-900 mb-3 font-semibold">Before onboarding a client, ensure:</p>
          <ul className="space-y-2 text-blue-800 text-sm">
            <li>✓ Client has an active Schwab brokerage account</li>
            <li>✓ Schwab OAuth credentials are configured (see <Link href="/docs/getting-started/schwab-oauth" className="underline font-medium">Schwab OAuth Setup</Link>)</li>
            <li>✓ ML and RL models are trained for desired strategies</li>
            <li>✓ Database is running and accessible</li>
          </ul>
        </div>
      </section>

      {/* Step 1: Add Client */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 1: Add Client to Database</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-100 rounded-lg">
              <UserPlus className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Create Client Record</h3>
          </div>

          <p className="text-gray-700 mb-4 text-sm">Navigate to the Clients page and click "Add New Client":</p>

          <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-xs mb-4">
            # Or use the API directly:<br/>
            curl -X POST http://localhost:8000/api/clients \<br/>
            &nbsp;&nbsp;-H &quot;Content-Type: application/json&quot; \<br/>
            &nbsp;&nbsp;-d &apos;&#123;<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;&quot;name&quot;: &quot;John Doe&quot;,<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;&quot;email&quot;: &quot;john.doe@example.com&quot;,<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;&quot;phone&quot;: &quot;555-1234&quot;,<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;&quot;risk_tolerance&quot;: &quot;moderate&quot;,<br/>
            &nbsp;&nbsp;&nbsp;&nbsp;&quot;investment_goals&quot;: &quot;long-term growth&quot;<br/>
            &nbsp;&nbsp;&#125;&apos;
          </div>

          <div className="bg-gray-50 p-4 rounded text-sm">
            <p className="font-semibold text-gray-900 mb-2">Required Fields:</p>
            <ul className="space-y-1 text-gray-700">
              <li><code className="bg-gray-200 px-1 py-0.5 rounded text-xs">name</code> - Client's full name</li>
              <li><code className="bg-gray-200 px-1 py-0.5 rounded text-xs">email</code> - Contact email</li>
              <li><code className="bg-gray-200 px-1 py-0.5 rounded text-xs">risk_tolerance</code> - conservative | moderate | aggressive</li>
              <li><code className="bg-gray-200 px-1 py-0.5 rounded text-xs">investment_goals</code> - Description of investment objectives</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Step 2: Connect Brokerage */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 2: Connect Brokerage Account</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose mb-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-100 rounded-lg">
              <Building2 className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Schwab OAuth Flow</h3>
          </div>

          <ol className="space-y-4 text-sm text-gray-700">
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">1</span>
              <div>
                <p className="font-semibold text-gray-900 mb-1">Navigate to Brokerages Page</p>
                <p>From the client detail page, click "Connect Brokerage Account"</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">2</span>
              <div>
                <p className="font-semibold text-gray-900 mb-1">Select Schwab and Initiate OAuth</p>
                <p>Click "Connect Schwab" - this will redirect to Schwab's login page</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">3</span>
              <div>
                <p className="font-semibold text-gray-900 mb-1">Client Authorizes Access</p>
                <p>Client logs into Schwab and grants ACIS AI permission to access their account</p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">4</span>
              <div>
                <p className="font-semibold text-gray-900 mb-1">Tokens Stored Securely</p>
                <p>OAuth access and refresh tokens are encrypted and stored in the database</p>
              </div>
            </li>
          </ol>

          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-xs">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-yellow-900 mb-1">Important: Redirect URI</p>
                <p className="text-yellow-800">Ensure your Schwab app's redirect URI matches your ngrok URL or production domain. Update <code>NEXTAUTH_URL</code> in <code>.env</code> if needed.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Step 3: Configure Strategy */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 3: Configure Trading Strategy</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose">
          <p className="text-gray-700 mb-4 text-sm">Assign the client's preferred strategy and market cap segment:</p>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="font-semibold text-gray-900 mb-2 text-sm">Available Strategies:</p>
              <ul className="space-y-1 text-xs text-gray-700">
                <li>• <strong>Growth:</strong> High-growth potential stocks</li>
                <li>• <strong>Momentum:</strong> Strong price trends</li>
                <li>• <strong>Value:</strong> Undervalued fundamentals</li>
                <li>• <strong>Dividend:</strong> High dividend yield</li>
              </ul>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <p className="font-semibold text-gray-900 mb-2 text-sm">Market Cap Segments:</p>
              <ul className="space-y-1 text-xs text-gray-700">
                <li>• <strong>Large:</strong> {'>'} $10B market cap</li>
                <li>• <strong>Mid:</strong> $2B - $10B</li>
                <li>• <strong>Small:</strong> {'<'} $2B</li>
              </ul>
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded text-xs text-blue-800">
            <p className="font-semibold mb-1">Autonomous Mode (Recommended):</p>
            <p>Enable autonomous trading to let the meta-model automatically select the best strategy based on current market conditions. The system will switch between strategies as market regimes change.</p>
          </div>
        </div>
      </section>

      {/* Step 4: Verify */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 4: Verify Connection</h2>
        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose">
          <p className="text-gray-700 mb-4 text-sm">Confirm the client's account is properly connected:</p>

          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-semibold text-gray-900">Account Balance Visible</p>
                <p className="text-gray-600">View current cash and positions on client detail page</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-semibold text-gray-900">OAuth Status: Active</p>
                <p className="text-gray-600">Green indicator shows tokens are valid</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="font-semibold text-gray-900">Trading Enabled</p>
                <p className="text-gray-600">Client appears in trading dashboard</p>
              </div>
            </div>
          </div>

          <div className="mt-4 bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs">
            # Test API connection:<br/>
            curl http://localhost:8000/api/clients/1/account-info
          </div>
        </div>
      </section>

      {/* Next Steps */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Next Steps</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
          <Link href="/docs/getting-started/first-rebalance" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Execute First Rebalance</h3>
                <p className="text-sm text-gray-600">Generate and execute initial portfolio</p>
              </div>
              <ArrowRight className="w-5 h-5 text-gray-400" />
            </div>
          </Link>
          <Link href="/docs/operations" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900 mb-1">Operations Manual</h3>
                <p className="text-sm text-gray-600">Daily monitoring and maintenance</p>
              </div>
              <ArrowRight className="w-5 h-5 text-gray-400" />
            </div>
          </Link>
        </div>
      </section>

      {/* Troubleshooting */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Troubleshooting</h2>
        <div className="space-y-4 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="font-semibold text-gray-900 mb-2 text-sm">OAuth Callback Failed</p>
            <p className="text-gray-600 text-xs mb-2">Check ngrok is running and redirect URI matches in Schwab developer portal</p>
            <code className="bg-gray-900 text-gray-100 px-2 py-1 rounded text-xs">ngrok http 3000</code>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="font-semibold text-gray-900 mb-2 text-sm">Account Balance Shows $0</p>
            <p className="text-gray-600 text-xs mb-2">Tokens may have expired. Re-authenticate from Brokerages page</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="font-semibold text-gray-900 mb-2 text-sm">Client Not Appearing in Trading Dashboard</p>
            <p className="text-gray-600 text-xs mb-2">Ensure trading is enabled and strategy is configured</p>
          </div>
        </div>
      </section>
    </div>
  )
}
