'use client'

import Link from 'next/link'
import { AlertTriangle, CheckCircle2, XCircle, Info } from 'lucide-react'

export default function Troubleshooting() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Troubleshooting Guide</h1>
      <p className="text-xl text-gray-600 mb-8">
        Common issues and their solutions for the ACIS AI Platform.
      </p>

      {/* Database Issues */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Database Issues</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">Connection Failed</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> API errors, "database connection failed"</p>
          <p className="text-gray-700 mb-3"><strong>Solutions:</strong></p>
          <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-sm mb-3">
            # Check if PostgreSQL is running<br/>
            sudo systemctl status postgresql<br/><br/>
            # Restart if needed<br/>
            sudo systemctl restart postgresql<br/><br/>
            # Test connection<br/>
            PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -c "SELECT 1"
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">Missing Data</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> No stocks returned, empty portfolio recommendations</p>
          <p className="text-gray-700 mb-3"><strong>Solutions:</strong></p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li>Run the data pipeline: <code>./scripts/run_eod_pipeline.sh</code></li>
            <li>Check the <code>ml_training_features</code> view has recent data</li>
            <li>Verify Alpha Vantage API key is valid</li>
          </ol>
        </div>
      </section>

      {/* Model Training Issues */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Model Training Issues</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">Training Fails with "No Model Found"</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> Incremental training fails, "no existing model"</p>
          <p className="text-gray-700 mb-3"><strong>Solution:</strong> Run full retraining first</p>
          <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-sm">
            # For ML models<br/>
            python ml_models/incremental_train_xgboost.py --strategy growth --market-cap mid --mode full<br/><br/>
            # For RL agents<br/>
            python rl_trading/incremental_train_ppo.py --strategy growth --market-cap mid --mode full --timesteps 1000000
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">GPU Out of Memory</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> CUDA out of memory errors during RL training</p>
          <p className="text-gray-700 mb-3"><strong>Solutions:</strong></p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li>Reduce batch size in RL training config</li>
            <li>Use CPU instead: <code>--device cpu</code></li>
            <li>Check GPU memory: <code>nvidia-smi</code></li>
            <li>Close other GPU processes</li>
          </ol>
        </div>
      </section>

      {/* Schwab OAuth Issues */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Schwab OAuth Issues</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">Token Expired</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> "Access token expired", API 401 errors</p>
          <p className="text-gray-700 mb-3"><strong>Solution:</strong> Re-authenticate the client</p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li>Go to Brokerages page</li>
            <li>Click "Re-authenticate" for the affected brokerage</li>
            <li>Complete OAuth flow in new window</li>
          </ol>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">OAuth Redirect Failed</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> Redirect URL not reachable, OAuth callback never completes</p>
          <p className="text-gray-700 mb-3"><strong>Solutions:</strong></p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li>Check ngrok is running: <code>ngrok http 3000</code></li>
            <li>Update redirect URI in Schwab developer portal</li>
            <li>Verify <code>.env</code> has correct <code>NEXTAUTH_URL</code></li>
          </ol>
        </div>
      </section>

      {/* Trading Issues */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Trading Issues</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">Orders Rejected</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> Orders fail to execute, "insufficient funds", "invalid quantity"</p>
          <p className="text-gray-700 mb-3"><strong>Solutions:</strong></p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li>Verify account has sufficient buying power</li>
            <li>Check position limits and drift thresholds</li>
            <li>Ensure orders are during market hours (9:30 AM - 4:00 PM ET)</li>
            <li>Review order logs in <code>logs/trading/</code></li>
          </ol>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">No Recommendations Generated</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Symptoms:</strong> Empty recommendation list after running rebalance</p>
          <p className="text-gray-700 mb-3"><strong>Causes & Solutions:</strong></p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li><strong>Drift too low:</strong> Portfolio already balanced, no rebalance needed</li>
            <li><strong>Missing models:</strong> Train ML/RL models first</li>
            <li><strong>No eligible stocks:</strong> Check ML model filtering criteria</li>
          </ol>
        </div>
      </section>

      {/* Performance Issues */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Performance Issues</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 not-prose">
          <div className="flex items-start gap-3 mb-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <h3 className="text-lg font-semibold text-gray-900">Slow API Responses</h3>
          </div>
          <p className="text-gray-700 mb-3"><strong>Solutions:</strong></p>
          <ol className="list-decimal pl-5 space-y-2 text-gray-700">
            <li>Check database query performance: <code>EXPLAIN ANALYZE</code></li>
            <li>Vacuum database: <code>VACUUM ANALYZE</code></li>
            <li>Review API logs for slow endpoints</li>
            <li>Increase API worker count if needed</li>
          </ol>
        </div>
      </section>

      {/* System Status Checks */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">System Health Checks</h2>

        <div className="bg-blue-50 border border-blue-200 p-6 rounded-lg not-prose">
          <h3 className="font-semibold text-blue-900 mb-3">Quick Diagnostic Commands</h3>
          <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm space-y-2">
            # Check all services<br/>
            curl http://localhost:8000/health<br/><br/>
            # Check database<br/>
            PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -c "SELECT COUNT(*) FROM daily_bars"<br/><br/>
            # Check disk space<br/>
            df -h<br/><br/>
            # Check memory<br/>
            free -h<br/><br/>
            # Check GPU<br/>
            nvidia-smi
          </div>
        </div>
      </section>

      {/* Get Help */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Still Need Help?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
          <Link href="/admin" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">System Admin</h3>
            <p className="text-sm text-gray-600">Check system status and view logs</p>
          </Link>
          <Link href="/docs/operations" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Operations Manual</h3>
            <p className="text-sm text-gray-600">Review operational procedures</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
