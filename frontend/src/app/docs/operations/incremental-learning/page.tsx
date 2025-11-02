'use client'

import Link from 'next/link'
import { Zap, GraduationCap, Clock, RotateCcw, GitBranch, AlertTriangle } from 'lucide-react'

export default function IncrementalLearning() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Incremental Learning System</h1>
      <p className="text-xl text-gray-600 mb-8">
        Fast daily model updates combined with comprehensive periodic retraining for optimal performance.
      </p>

      {/* Overview */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Overview</h2>
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-6 not-prose mb-6">
          <p className="text-gray-800 leading-relaxed">
            The ACIS AI Platform supports <strong>incremental learning</strong> for both ML (XGBoost) and RL (PPO) models.
            This hybrid approach allows for fast daily updates while maintaining periodic full retraining for optimal performance.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 not-prose mb-8">
          {/* Full Retraining */}
          <div className="bg-white border-2 border-green-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <GraduationCap className="w-6 h-6 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Full Retraining</h3>
            </div>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Trains from scratch on entire historical dataset</li>
              <li>• Duration: 30-60 min (ML), 2-4 hours (RL)</li>
              <li>• Schedule: Weekly (ML), Monthly (RL)</li>
              <li>• Comprehensive model updates</li>
            </ul>
          </div>

          {/* Incremental Updates */}
          <div className="bg-white border-2 border-purple-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <Zap className="w-6 h-6 text-purple-600" />
              <h3 className="text-lg font-semibold text-gray-900">Incremental Updates</h3>
            </div>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• Fine-tunes existing models on recent data</li>
              <li>• Duration: 5-10 min (ML), 20-30 min (RL)</li>
              <li>• Schedule: Daily</li>
              <li>• Quick adaptation to market changes</li>
            </ul>
          </div>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Benefits</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <h4 className="font-semibold text-purple-900 mb-2">Incremental Learning:</h4>
            <ul className="space-y-1 text-sm text-purple-800">
              <li>⚡ Fast: 5-10x faster than full retraining</li>
              <li>🎯 Adaptive: Quickly responds to recent data</li>
              <li>💾 Efficient: Uses only last N days of data</li>
              <li>🔄 Continuous: Can run daily without heavy compute</li>
            </ul>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h4 className="font-semibold text-green-900 mb-2">Full Retraining:</h4>
            <ul className="space-y-1 text-sm text-green-800">
              <li>🎓 Comprehensive: Learns from entire history</li>
              <li>🔍 Robust: Avoids concept drift accumulation</li>
              <li>📊 Stable: Maintains long-term performance</li>
              <li>🏛️ Foundation: Solid baseline for incremental updates</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ML Models (XGBoost) */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">ML Models (XGBoost)</h2>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Full Retraining</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          python ml_models/incremental_train_xgboost.py \<br/>
          &nbsp;&nbsp;--strategy growth \<br/>
          &nbsp;&nbsp;--market-cap mid \<br/>
          &nbsp;&nbsp;--mode full \<br/>
          &nbsp;&nbsp;--gpu 0
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Incremental Update</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          python ml_models/incremental_train_xgboost.py \<br/>
          &nbsp;&nbsp;--strategy growth \<br/>
          &nbsp;&nbsp;--market-cap mid \<br/>
          &nbsp;&nbsp;--mode incremental \<br/>
          &nbsp;&nbsp;--days 7 \<br/>
          &nbsp;&nbsp;--iterations 100
        </div>

        <div className="bg-blue-50 border border-blue-200 p-4 rounded text-sm not-prose">
          <strong>Key Parameters:</strong>
          <ul className="mt-2 space-y-1">
            <li>• <code className="text-sm">--mode</code>: "full" or "incremental"</li>
            <li>• <code className="text-sm">--days</code>: Number of recent days for incremental (default: 7)</li>
            <li>• <code className="text-sm">--iterations</code>: Trees to add incrementally (default: 100)</li>
          </ul>
        </div>
      </section>

      {/* RL Agents (PPO) */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">RL Agents (PPO)</h2>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Full Retraining</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          python rl_trading/incremental_train_ppo.py \<br/>
          &nbsp;&nbsp;--strategy growth \<br/>
          &nbsp;&nbsp;--market-cap mid \<br/>
          &nbsp;&nbsp;--mode full \<br/>
          &nbsp;&nbsp;--timesteps 1000000 \<br/>
          &nbsp;&nbsp;--device cuda
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Incremental Update</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-6 not-prose">
          python rl_trading/incremental_train_ppo.py \<br/>
          &nbsp;&nbsp;--strategy growth \<br/>
          &nbsp;&nbsp;--market-cap mid \<br/>
          &nbsp;&nbsp;--mode incremental \<br/>
          &nbsp;&nbsp;--timesteps 50000 \<br/>
          &nbsp;&nbsp;--device cuda
        </div>

        <div className="bg-blue-50 border border-blue-200 p-4 rounded text-sm not-prose">
          <strong>Key Parameters:</strong>
          <ul className="mt-2 space-y-1">
            <li>• <code className="text-sm">--mode</code>: "full" or "incremental"</li>
            <li>• <code className="text-sm">--timesteps</code>: Training steps (1M full, 50K incremental)</li>
            <li>• <code className="text-sm">--device</code>: "cuda", "cpu", or "auto"</li>
          </ul>
        </div>
      </section>

      {/* Automated Daily Updates */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Automated Daily Updates</h2>
        <p>Run the automated daily update script:</p>

        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm mb-4 not-prose">
          ./scripts/run_daily_incremental_update.sh
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 not-prose">
          <h4 className="font-semibold text-purple-900 mb-2">This script:</h4>
          <ul className="space-y-1 text-sm text-purple-800">
            <li>• Updates all 9 ML models (3 strategies × 3 market caps)</li>
            <li>• Optionally updates all 9 RL agents (disabled by default)</li>
            <li>• Takes ~5-10 minutes (ML only)</li>
            <li>• Logs results to <code>logs/daily_updates/</code></li>
          </ul>
        </div>
      </section>

      {/* Scheduling */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Recommended Schedule</h2>

        <div className="grid grid-cols-1 gap-4 not-prose mb-6">
          <div className="bg-white border-l-4 border-purple-500 p-4 rounded-r">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-purple-600" />
              <strong className="text-purple-900">Daily (2:00 AM)</strong>
            </div>
            <p className="text-sm text-gray-700">Incremental ML updates (5-10 minutes)</p>
          </div>

          <div className="bg-white border-l-4 border-green-500 p-4 rounded-r">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-green-600" />
              <strong className="text-green-900">Weekly (Sunday 3:00 AM)</strong>
            </div>
            <p className="text-sm text-gray-700">Full ML retraining (30-60 minutes)</p>
          </div>

          <div className="bg-white border-l-4 border-blue-500 p-4 rounded-r">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-5 h-5 text-blue-600" />
              <strong className="text-blue-900">Monthly (1st, 4:00 AM)</strong>
            </div>
            <p className="text-sm text-gray-700">Full RL retraining (2-4 hours)</p>
          </div>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Crontab Setup</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm not-prose">
          # Edit crontab<br/>
          crontab -e<br/><br/>
          # Add schedules<br/>
          0 2 * * * /path/to/scripts/run_daily_incremental_update.sh<br/>
          0 3 * * 0 /path/to/scripts/run_weekly_ml_training.sh<br/>
          0 4 1 * * /path/to/scripts/run_monthly_rl_training.sh
        </div>
      </section>

      {/* Model Versioning & Rollback */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Model Versioning & Rollback</h2>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Automatic Backups</h3>
        <p>All model updates automatically create backups:</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose mb-6">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">ML Models:</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              <li>• Location: <code className="text-xs">models/ml/backups/</code></li>
              <li>• Format: <code className="text-xs">{'modelname_timestamp.json'}</code></li>
              <li>• Keeps: Last 10 backups per model</li>
            </ul>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2">RL Agents:</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              <li>• Location: <code className="text-xs">models/rl/backups/</code></li>
              <li>• Format: <code className="text-xs">{'ppo_hybrid_*_timestamp.zip'}</code></li>
              <li>• Keeps: Last 10 backups per agent</li>
            </ul>
          </div>
        </div>

        <h3 className="text-xl font-bold text-gray-900 mb-3">Rollback to Previous Version</h3>
        <div className="bg-gray-900 text-gray-100 p-4 rounded-lg font-mono text-sm not-prose">
          # List backups<br/>
          ls -lh models/ml/backups/growth_midcap_*.json<br/><br/>
          # Restore backup<br/>
          cp models/ml/backups/growth_midcap_20251102_140532.json \<br/>
          &nbsp;&nbsp;&nbsp;models/ml/growth_midcap.json
        </div>
      </section>

      {/* Metadata Tracking */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Metadata Tracking</h2>
        <p>Each model stores training metadata for monitoring and debugging:</p>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 not-prose">
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">ML Metadata Example:</h4>
            <div className="bg-gray-900 text-gray-100 p-3 rounded-lg font-mono text-xs overflow-x-auto">
              {'{'}<br/>
              &nbsp;&nbsp;"strategy": "growth",<br/>
              &nbsp;&nbsp;"market_cap_segment": "mid",<br/>
              &nbsp;&nbsp;"last_trained_date": "2025-11-02",<br/>
              &nbsp;&nbsp;"n_samples": 245678,<br/>
              &nbsp;&nbsp;"train_correlation": 0.423,<br/>
              &nbsp;&nbsp;"mode": "incremental",<br/>
              &nbsp;&nbsp;"incremental_samples": 1234<br/>
              {'}'}
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-2">RL Metadata Example:</h4>
            <div className="bg-gray-900 text-gray-100 p-3 rounded-lg font-mono text-xs overflow-x-auto">
              {'{'}<br/>
              &nbsp;&nbsp;"strategy": "growth",<br/>
              &nbsp;&nbsp;"market_cap_segment": "mid",<br/>
              &nbsp;&nbsp;"last_trained_date": "2025-11-02",<br/>
              &nbsp;&nbsp;"total_timesteps": 1050000,<br/>
              &nbsp;&nbsp;"mode": "incremental",<br/>
              &nbsp;&nbsp;"incremental_timesteps": 50000<br/>
              {'}'}
            </div>
          </div>
        </div>
      </section>

      {/* Best Practices */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Best Practices</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 not-prose">
          <div className="bg-green-50 border-2 border-green-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-green-900 mb-3 flex items-center gap-2">
              <GraduationCap className="w-5 h-5" />
              Use Full Retraining When:
            </h3>
            <ul className="space-y-2 text-sm text-green-800">
              <li>✅ Monthly/weekly scheduled maintenance</li>
              <li>✅ Significant market regime changes</li>
              <li>✅ Adding new features to models</li>
              <li>✅ Model performance degrades significantly</li>
              <li>✅ After major market events</li>
            </ul>
          </div>

          <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-purple-900 mb-3 flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Use Incremental Updates When:
            </h3>
            <ul className="space-y-2 text-sm text-purple-800">
              <li>✅ Daily/continuous adaptation needed</li>
              <li>✅ Quick response to recent data</li>
              <li>✅ Computational resources limited</li>
              <li>✅ Testing new strategies rapidly</li>
              <li>✅ Between full retraining cycles</li>
            </ul>
          </div>
        </div>

        <div className="mt-6 bg-yellow-50 border-l-4 border-yellow-600 p-4 not-prose">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-yellow-900 mb-2">Monitoring Model Performance</p>
              <p className="text-sm text-yellow-800 mb-2">Track these metrics to decide when full retraining is needed:</p>
              <ul className="text-sm text-yellow-800 space-y-1">
                <li>• ML: Spearman correlation, prediction error trends</li>
                <li>• RL: Sharpe ratio, portfolio returns, drawdown</li>
              </ul>
              <p className="text-sm text-yellow-800 mt-2"><strong>Triggers for Full Retraining:</strong></p>
              <ul className="text-sm text-yellow-800 space-y-1">
                <li>• Correlation drops &gt; 10% from baseline</li>
                <li>• Sharpe ratio &lt; 0.5</li>
                <li>• Maximum drawdown &gt; 30%</li>
                <li>• Model hasn't been fully retrained in 30 days</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Performance Comparison */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Performance Comparison</h2>

        <div className="overflow-x-auto not-prose">
          <table className="min-w-full bg-white border border-gray-200 rounded-lg">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">Mode</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">ML Time</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">RL Time</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">Data Used</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">Use Case</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">Full</td>
                <td className="px-4 py-3 text-sm text-gray-700">30-60 min</td>
                <td className="px-4 py-3 text-sm text-gray-700">2-4 hours</td>
                <td className="px-4 py-3 text-sm text-gray-700">2015-2023 (8 years)</td>
                <td className="px-4 py-3 text-sm text-gray-700">Comprehensive monthly/weekly</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">Incremental</td>
                <td className="px-4 py-3 text-sm text-gray-700">5-10 min</td>
                <td className="px-4 py-3 text-sm text-gray-700">20-30 min</td>
                <td className="px-4 py-3 text-sm text-gray-700">Last 7 days</td>
                <td className="px-4 py-3 text-sm text-gray-700">Daily quick adaptation</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded text-sm not-prose">
          <strong>Speedup:</strong> 6-10x faster for incremental updates
        </div>
      </section>

      {/* Summary */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Summary</h2>
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-200 rounded-lg p-6 not-prose">
          <p className="text-gray-800 mb-4 font-semibold">The incremental learning system provides:</p>
          <ul className="space-y-2 text-gray-800">
            <li className="flex items-start gap-2">
              <Zap className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <span><strong>Fast daily updates</strong> (5-10 minutes) for quick adaptation</span>
            </li>
            <li className="flex items-start gap-2">
              <GraduationCap className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <span><strong>Comprehensive periodic retraining</strong> for robust long-term performance</span>
            </li>
            <li className="flex items-start gap-2">
              <GitBranch className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <span><strong>Automatic versioning</strong> with rollback capability</span>
            </li>
            <li className="flex items-start gap-2">
              <RotateCcw className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
              <span><strong>Flexible scheduling</strong> via scripts and cron</span>
            </li>
          </ul>
          <p className="text-gray-700 mt-4 italic">
            This hybrid approach combines the best of both worlds: rapid adaptation to recent market changes and
            stable long-term performance from comprehensive retraining.
          </p>
        </div>
      </section>

      {/* Related Pages */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Related Documentation</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 not-prose">
          <Link href="/docs/operations" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Operations Manual</h3>
            <p className="text-sm text-gray-600">Daily, weekly, and monthly operational procedures</p>
          </Link>
          <Link href="/admin" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">System Admin</h3>
            <p className="text-sm text-gray-600">Monitor system status and trigger training jobs</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
