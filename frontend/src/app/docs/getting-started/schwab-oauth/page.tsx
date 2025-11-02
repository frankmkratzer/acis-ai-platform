'use client'

import { AlertCircle, CheckCircle, ExternalLink } from 'lucide-react'

export default function SchwabOAuthGuide() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Schwab OAuth Setup</h1>
      <p className="text-xl text-gray-600 mb-8">
        Configure OAuth authentication to integrate with Charles Schwab brokerage accounts.
      </p>

      {/* Prerequisites */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Prerequisites</h2>
        <ul className="space-y-2">
          <li>Active Charles Schwab brokerage account</li>
          <li>Schwab Developer Portal account</li>
          <li>ngrok installed and running (for OAuth callbacks)</li>
          <li>ACIS AI Platform backend running</li>
        </ul>
      </section>

      {/* Step 1: Schwab Developer Portal */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 1: Create Schwab Developer App</h2>

        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose mb-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-900 mb-1">Important</p>
              <p className="text-sm text-blue-800">
                You must complete this setup in the Schwab Developer Portal before proceeding.
              </p>
            </div>
          </div>
        </div>

        <ol className="space-y-4">
          <li>
            <strong>Visit Schwab Developer Portal</strong>
            <div className="mt-2 flex items-center gap-2">
              <a
                href="https://developer.schwab.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline flex items-center gap-1"
              >
                https://developer.schwab.com
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </li>

          <li>
            <strong>Register an Application</strong>
            <ul className="mt-2 space-y-1 ml-4">
              <li>• Log in to your developer account</li>
              <li>• Navigate to "My Apps" → "Create New App"</li>
              <li>• Fill in application details:
                <ul className="ml-4 mt-1 space-y-1">
                  <li>- <strong>Name:</strong> ACIS AI Platform</li>
                  <li>- <strong>Description:</strong> Autonomous investment management</li>
                  <li>- <strong>Redirect URI:</strong> <code className="text-sm">https://YOUR-NGROK-URL.ngrok.io/api/schwab/callback</code></li>
                </ul>
              </li>
            </ul>
          </li>

          <li>
            <strong>Copy Credentials</strong>
            <p className="mt-2 text-gray-600">After creating the app, copy these values:</p>
            <ul className="mt-2 space-y-1 ml-4">
              <li>• Client ID (App Key)</li>
              <li>• Client Secret (App Secret)</li>
            </ul>
          </li>
        </ol>
      </section>

      {/* Step 2: Configure ngrok */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 2: Start ngrok Tunnel</h2>
        <p className="mb-4">
          Schwab OAuth requires HTTPS callbacks. ngrok provides a secure tunnel to your local development server.
        </p>

        <h3 className="text-xl font-semibold text-gray-900 mb-3">Start ngrok</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-4 not-prose">
          ngrok http 8000
        </div>

        <p className="mb-4">ngrok will display output like this:</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-4 not-prose">
          Forwarding https://abc123def456.ngrok.io -&gt; http://localhost:8000
        </div>

        <p className="mb-4">Copy the HTTPS URL (e.g., <code>https://abc123def456.ngrok.io</code>)</p>

        <div className="bg-yellow-50 border-l-4 border-yellow-600 p-4 not-prose mb-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-900 mb-1">ngrok URL Changes</p>
              <p className="text-sm text-yellow-800">
                Free ngrok URLs change each time you restart ngrok. Update your Schwab app's Redirect URI
                whenever the URL changes. Consider using ngrok's paid plan for a static domain.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Step 3: Configure Environment */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 3: Configure Backend Environment</h2>
        <p className="mb-4">Update your <code>backend/.env</code> file with Schwab credentials:</p>

        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-4 not-prose">
          SCHWAB_CLIENT_ID=your_app_key_here<br/>
          SCHWAB_CLIENT_SECRET=your_app_secret_here<br/>
          SCHWAB_REDIRECT_URI=https://your-ngrok-url.ngrok.io/api/schwab/callback
        </div>

        <p className="mb-4">Restart the backend server to apply changes:</p>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-4 not-prose">
          # Stop the current server (Ctrl+C)<br/>
          # Restart:<br/>
          cd backend<br/>
          source ../venv/bin/activate<br/>
          uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
        </div>
      </section>

      {/* Step 4: Test OAuth Flow */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Step 4: Test OAuth Flow</h2>

        <ol className="space-y-4">
          <li>
            <strong>Navigate to Client Page</strong>
            <p className="mt-2 text-gray-600">In the ACIS AI frontend, go to a client's detail page</p>
          </li>

          <li>
            <strong>Click "Connect Schwab"</strong>
            <p className="mt-2 text-gray-600">This will redirect you to Schwab's login page</p>
          </li>

          <li>
            <strong>Authorize Access</strong>
            <p className="mt-2 text-gray-600">
              Log in with your Schwab credentials and grant permission to ACIS AI
            </p>
          </li>

          <li>
            <strong>Verify Connection</strong>
            <p className="mt-2 text-gray-600">
              After authorization, you'll be redirected back to ACIS AI. The client should now show "Connected"
              status with access to Schwab account data.
            </p>
          </li>
        </ol>

        <div className="bg-green-50 border-l-4 border-green-600 p-4 not-prose mt-6">
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-green-900 mb-1">Success</p>
              <p className="text-sm text-green-800">
                If you see account balances and positions, OAuth is configured correctly!
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Troubleshooting */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Troubleshooting</h2>

        <div className="space-y-4">
          <div className="border-l-4 border-red-600 bg-red-50 p-4 not-prose">
            <h3 className="font-semibold text-red-900 mb-2">Error: redirect_uri_mismatch</h3>
            <p className="text-sm text-red-800 mb-2">
              <strong>Cause:</strong> Redirect URI in Schwab app doesn't match your configuration
            </p>
            <p className="text-sm text-red-800">
              <strong>Solution:</strong> Ensure both the Schwab Developer Portal app and your <code>.env</code> file
              use the exact same redirect URI (including https://)
            </p>
          </div>

          <div className="border-l-4 border-red-600 bg-red-50 p-4 not-prose">
            <h3 className="font-semibold text-red-900 mb-2">Error: invalid_client</h3>
            <p className="text-sm text-red-800 mb-2">
              <strong>Cause:</strong> Invalid Client ID or Client Secret
            </p>
            <p className="text-sm text-red-800">
              <strong>Solution:</strong> Double-check credentials in <code>.env</code> file match those in Schwab Developer Portal
            </p>
          </div>

          <div className="border-l-4 border-red-600 bg-red-50 p-4 not-prose">
            <h3 className="font-semibold text-red-900 mb-2">ngrok tunnel not working</h3>
            <p className="text-sm text-red-800 mb-2">
              <strong>Cause:</strong> ngrok not running or backend server not accessible
            </p>
            <p className="text-sm text-red-800">
              <strong>Solution:</strong> Ensure both ngrok and backend server are running. Test by visiting
              the ngrok URL in your browser.
            </p>
          </div>
        </div>
      </section>

      {/* Token Management */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Token Management</h2>
        <p className="mb-4">Schwab OAuth tokens expire after a period of time. ACIS AI automatically handles token refresh:</p>

        <ul className="space-y-2">
          <li>
            <strong>Access Token:</strong> Valid for 30 minutes, automatically refreshed when needed
          </li>
          <li>
            <strong>Refresh Token:</strong> Valid for 7 days, used to obtain new access tokens
          </li>
          <li>
            <strong>Re-authorization:</strong> If refresh token expires, client must re-authorize through OAuth flow
          </li>
        </ul>

        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose mt-6">
          <p className="text-sm text-blue-800">
            ACIS AI monitors token expiration and displays warnings in the UI when re-authorization is needed.
          </p>
        </div>
      </section>
    </div>
  )
}
