'use client'

import Link from 'next/link'
import { Calendar, RefreshCw, AlertTriangle, CheckCircle2 } from 'lucide-react'

export default function OperationsOverview() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Operations Manual</h1>
      <p className="text-xl text-gray-600 mb-8">
        Day-to-day operational procedures for running the ACIS AI Platform.
      </p>

      {/* Daily Operations Schedule */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Daily Operations Schedule</h2>

        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose mb-6">
          <div className="flex items-start gap-3">
            <Calendar className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-900 mb-1">Automated Schedule</p>
              <p className="text-sm text-blue-800">
                Most operations run automatically via cron jobs. Manual intervention only needed for exceptions.
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-4 not-prose mb-8">
          {/* Early Morning - Incremental Updates */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-semibold">
                2:00 AM ET
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Incremental ML Model Updates</h3>
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-semibold">NEW</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Fine-tune XGBoost Models:</strong> Update all 9 ML models with last 7 days of data
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Automatic Backups:</strong> Previous model versions saved to backups/ directory
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Quick Adaptation:</strong> Models stay current with recent market patterns
                </span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-purple-50 rounded text-xs text-purple-800">
              <strong>Script:</strong> <code>scripts/run_daily_incremental_update.sh</code><br/>
              <strong>Duration:</strong> ~5-10 minutes (6-10x faster than full retraining)<br/>
              <strong>Training Mode:</strong> Incremental (uses last 7 days, 100 iterations)<br/>
              <strong>Monitoring:</strong> Check logs at <code>logs/daily_updates/incremental_update_*.log</code>
            </div>
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800">
              <strong>📖 Learn More:</strong> See the <Link href="/docs/operations/incremental-learning" className="underline font-medium">Incremental Learning Guide</Link> for details on warm-start training and rollback procedures.
            </div>
          </div>

          {/* Morning */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-semibold">
                6:00 AM ET
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Daily Data Pipeline</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Database Validation:</strong> Check connectivity and data freshness
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Materialized Views:</strong> Refresh ml_training_features with latest data
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Database Maintenance:</strong> VACUUM ANALYZE on critical tables
                </span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded text-xs text-gray-600">
              <strong>Script:</strong> <code>scripts/run_daily_data_pipeline.sh</code><br/>
              <strong>Duration:</strong> ~5 minutes (optimized - no ML/RL training)<br/>
              <strong>Monitoring:</strong> Check logs at <code>logs/pipeline/daily_data_*.log</code> or System Admin page
            </div>
          </div>

          {/* Market Open */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
                9:30 AM ET
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Market Open</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>System Check:</strong> Verify all services (backend, frontend, database) are healthy
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>OAuth Status:</strong> Check Schwab connection status for all active clients
                </span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded text-xs text-gray-600">
              <strong>Endpoint:</strong> <code>GET /api/health</code> and <code>GET /api/autonomous/status</code>
            </div>
          </div>

          {/* Market Close */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
                4:30 PM ET
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Rebalancing Window</h3>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Market Regime Detection:</strong> Classify current market conditions
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Strategy Selection:</strong> Meta-model selects optimal strategy for each account
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Portfolio Analysis:</strong> Check drift thresholds, evaluate need for rebalance
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Trade Generation:</strong> If rebalance needed, generate ML+RL recommendations
                </span>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-gray-700">
                  <strong>Trade Execution:</strong> Submit trades to Schwab (paper or live mode)
                </span>
              </div>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded text-xs text-gray-600">
              <strong>Script:</strong> <code>scripts/run_daily_rebalance.py</code><br/>
              <strong>Duration:</strong> ~10-15 minutes<br/>
              <strong>Monitoring:</strong> Dashboard at <code>/autonomous-fund</code>
            </div>
          </div>
        </div>

        <div className="bg-yellow-50 border-l-4 border-yellow-600 p-4 not-prose">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-yellow-900 mb-1">Manual Review Required</p>
              <p className="text-sm text-yellow-800">
                On days with high drift (&gt;5%) or major market events, manually review trade recommendations
                before execution. Use the "Approve/Reject" workflow in the Trading page.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Weekly Operations */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Weekly Operations</h2>

        <div className="space-y-4 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <RefreshCw className="w-5 h-5 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Full ML Model Retraining</h3>
            </div>
            <p className="text-sm text-gray-700 mb-3">
              Every Sunday, perform full retraining from scratch on entire historical dataset:
            </p>
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-xs mb-3">
              # Automated via cron or manual trigger from System Admin page<br/>
              scripts/run_weekly_ml_training.sh
            </div>
            <div className="bg-blue-50 border border-blue-200 p-3 rounded text-xs text-blue-800 mb-3">
              <strong>Duration:</strong> ~30-60 minutes for all 9 models (3 strategies × 3 market caps)<br/>
              <strong>Training Mode:</strong> Full retraining on 2015-2023 data (prevents concept drift)<br/>
              <strong>Validation:</strong> Models automatically saved to <code>models/ml/</code><br/>
              <strong>Monitoring:</strong> Check logs at <code>logs/pipeline/weekly_ml_*.log</code> or System Admin page
            </div>
            <div className="p-3 bg-purple-50 border border-purple-200 rounded text-xs text-purple-800">
              <strong>🔄 Hybrid Training Strategy:</strong> Daily incremental updates (fast adaptation) + Weekly full retraining (robust long-term performance). Best of both worlds!
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <RefreshCw className="w-5 h-5 text-purple-600" />
              <h3 className="text-lg font-semibold text-gray-900">Performance Review</h3>
            </div>
            <p className="text-sm text-gray-700 mb-3">
              Every Monday morning, review the previous week's performance:
            </p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Compare each strategy's returns vs. benchmark (S&P 500)</li>
              <li>• Check Sharpe ratio, max drawdown, win rate</li>
              <li>• Identify underperforming strategies or outlier trades</li>
              <li>• Review rebalancing frequency and turnover costs</li>
            </ul>
            <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-600">
              <strong>Dashboard:</strong> Navigate to <code>/autonomous-fund</code> → Performance Metrics
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Client Communications</h3>
            </div>
            <p className="text-sm text-gray-700 mb-3">
              Send weekly performance summaries to active clients:
            </p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Portfolio value change (week and YTD)</li>
              <li>• Active strategy and reasoning</li>
              <li>• Number of trades executed</li>
              <li>• Any notable holdings or sector changes</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Monthly Operations */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Monthly Operations</h2>

        <div className="space-y-4 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Full RL Agent Retraining</h3>
            <p className="text-sm text-gray-700 mb-3">
              On the 1st of each month, perform full retraining from scratch for all PPO reinforcement learning agents:
            </p>
            <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-xs mb-3">
              # Automated via cron or manual trigger from System Admin page<br/>
              scripts/run_monthly_rl_training.sh
            </div>
            <div className="bg-purple-50 border border-purple-200 p-3 rounded text-xs text-purple-800">
              <strong>Duration:</strong> ~2-4 hours for all 9 agents (3 strategies × 3 market caps)<br/>
              <strong>Training Mode:</strong> Full retraining on 2015-2023 data with 1M timesteps<br/>
              <strong>GPU Recommended:</strong> Significantly faster with CUDA-enabled GPU<br/>
              <strong>Validation:</strong> Agents automatically saved to <code>models/rl/</code><br/>
              <strong>Monitoring:</strong> Check logs at <code>logs/pipeline/monthly_rl_*.log</code> or System Admin page
            </div>
            <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-600">
              <strong>Note:</strong> RL agents require pre-trained ML models. Ensure weekly ML training ran successfully before triggering monthly RL training.
            </div>
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800">
              <strong>💡 Optional Daily RL Updates:</strong> For more adaptive agents, you can enable daily incremental RL updates (20-30 min) by uncommenting the RL section in <code>scripts/run_daily_incremental_update.sh</code>. However, monthly full retraining is typically sufficient for most use cases.
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Database Maintenance</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Run <code>VACUUM ANALYZE</code> on all tables</li>
              <li>• Archive old trade execution records (&gt;1 year old)</li>
              <li>• Back up database to external storage</li>
              <li>• Check disk space usage and clean up old logs</li>
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Tax-Loss Harvesting Review</h3>
            <p className="text-sm text-gray-700 mb-2">
              For clients with tax optimization enabled, review opportunities:
            </p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Identify positions with unrealized losses</li>
              <li>• Check wash-sale rules (30-day window)</li>
              <li>• Coordinate harvesting with rebalancing schedule</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Quarterly Operations */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Quarterly Operations</h2>

        <div className="space-y-4 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Strategy Performance Audit</h3>
            <p className="text-sm text-gray-700 mb-3">
              Deep dive into each strategy's performance over the past quarter:
            </p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Run full backtest on quarter's data</li>
              <li>• Compare actual vs. backtested results (implementation shortfall)</li>
              <li>• Analyze attribution: which factors drove returns?</li>
              <li>• Consider strategy retirement if underperforming &gt;6 months</li>
            </ul>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Client Portfolio Reviews</h3>
            <p className="text-sm text-gray-700 mb-2">
              Meet with each active client to review:
            </p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Quarterly returns vs. goals</li>
              <li>• Risk tolerance assessment (any changes needed?)</li>
              <li>• Rebalancing frequency and drift settings</li>
              <li>• Tax situation and optimization strategies</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Emergency Procedures */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Emergency Procedures</h2>

        <div className="bg-red-50 border-l-4 border-red-600 p-6 not-prose mb-6">
          <h3 className="font-semibold text-red-900 mb-3">Market Crisis Protocol</h3>
          <p className="text-sm text-red-800 mb-3">
            In the event of extreme market volatility (VIX &gt; 40, S&P 500 down &gt;5% intraday):
          </p>
          <ol className="space-y-2 text-sm text-red-800 list-decimal list-inside">
            <li><strong>Pause autonomous trading</strong> - Disable auto_trading_enabled for all clients</li>
            <li><strong>Review all open positions</strong> - Check for margin calls or illiquid holdings</li>
            <li><strong>Manual rebalancing only</strong> - Switch from algorithmic to human oversight</li>
            <li><strong>Client communication</strong> - Notify clients of pause and action plan</li>
            <li><strong>Resume gradually</strong> - Re-enable automation after volatility normalizes</li>
          </ol>
        </div>

        <div className="bg-orange-50 border-l-4 border-orange-600 p-6 not-prose">
          <h3 className="font-semibold text-orange-900 mb-3">System Outage Protocol</h3>
          <p className="text-sm text-orange-800 mb-3">
            If critical systems (database, API, Schwab connection) fail:
          </p>
          <ol className="space-y-2 text-sm text-orange-800 list-decimal list-inside">
            <li><strong>Check service status</strong> - Run health checks on all components</li>
            <li><strong>Fail over to backup</strong> - Use read replica for database, restart services</li>
            <li><strong>Halt trading</strong> - Prevent erroneous trades during outage</li>
            <li><strong>Notify clients</strong> - If outage &gt;1 hour, send status update</li>
            <li><strong>Post-mortem</strong> - Document root cause and prevention steps</li>
          </ol>
        </div>
      </section>

      {/* Detailed Guides */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Detailed Operational Guides</h2>
        <div className="grid grid-cols-1 gap-4 not-prose">
          <Link href="/docs/operations/daily-operations" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Daily Operations Checklist</h3>
            <p className="text-sm text-gray-600">Step-by-step guide for daily tasks and monitoring</p>
          </Link>

          <Link href="/docs/operations/model-retraining" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Model Retraining Guide</h3>
            <p className="text-sm text-gray-600">How to retrain ML and RL models with new data</p>
          </Link>

          <Link href="/docs/operations/rebalancing" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Rebalancing Process</h3>
            <p className="text-sm text-gray-600">Understanding and managing the rebalancing workflow</p>
          </Link>

          <Link href="/docs/operations/monitoring" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Monitoring & Alerts</h3>
            <p className="text-sm text-gray-600">System health monitoring and alert configuration</p>
          </Link>

          <Link href="/docs/operations/troubleshooting" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Troubleshooting Guide</h3>
            <p className="text-sm text-gray-600">Common issues and how to resolve them</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
