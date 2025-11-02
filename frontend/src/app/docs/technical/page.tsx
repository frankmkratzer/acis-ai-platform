'use client'

import Link from 'next/link'
import { Database, Server, Cpu, GitBranch } from 'lucide-react'

export default function TechnicalDocs() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Technical Documentation</h1>
      <p className="text-xl text-gray-600 mb-8">
        System architecture, implementation details, and developer reference.
      </p>

      {/* Architecture Overview */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">System Architecture</h2>

        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6 not-prose mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Three-Tier Architecture</h3>
          <p className="text-sm text-gray-700">
            ACIS AI follows a modern three-tier architecture with clear separation of concerns between
            presentation (Next.js), business logic (FastAPI), and data (PostgreSQL).
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 not-prose mb-8">
          <div className="bg-white border-2 border-blue-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Server className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Frontend</h3>
            </div>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• <strong>Framework:</strong> Next.js 14 (App Router)</li>
              <li>• <strong>Language:</strong> TypeScript</li>
              <li>• <strong>Styling:</strong> Tailwind CSS</li>
              <li>• <strong>State:</strong> React hooks + API client</li>
              <li>• <strong>Port:</strong> 3000 (dev)</li>
            </ul>
          </div>

          <div className="bg-white border-2 border-purple-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <GitBranch className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Backend</h3>
            </div>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• <strong>Framework:</strong> FastAPI (Python 3.11+)</li>
              <li>• <strong>ORM:</strong> SQLAlchemy</li>
              <li>• <strong>Auth:</strong> HTTP Basic Auth</li>
              <li>• <strong>APIs:</strong> Schwab, Alpha Vantage</li>
              <li>• <strong>Port:</strong> 8000</li>
            </ul>
          </div>

          <div className="bg-white border-2 border-green-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Database className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Database</h3>
            </div>
            <ul className="space-y-2 text-sm text-gray-700">
              <li>• <strong>RDBMS:</strong> PostgreSQL 14+</li>
              <li>• <strong>Size:</strong> ~50GB (10 years market data)</li>
              <li>• <strong>Tables:</strong> 30+ normalized tables</li>
              <li>• <strong>Indexes:</strong> Optimized for time-series queries</li>
              <li>• <strong>Port:</strong> 5432</li>
            </ul>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <Cpu className="w-6 h-6 text-orange-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">ML/RL Infrastructure</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">ML Training (XGBoost)</h4>
              <ul className="space-y-1 text-gray-700">
                <li>• CPU-based training (multi-core)</li>
                <li>• scikit-learn pipeline</li>
                <li>• Model versioning with timestamps</li>
                <li>• Training time: ~30 min per model</li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">RL Training (PPO)</h4>
              <ul className="space-y-1 text-gray-700">
                <li>• GPU-accelerated (JAX)</li>
                <li>• NVIDIA CUDA 12.1+</li>
                <li>• Gymnasium environment</li>
                <li>• Training time: ~3 hours per agent</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack Details */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Technology Stack</h2>

        <div className="space-y-4 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Backend Technologies</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">Core Framework</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>FastAPI:</strong> High-performance async API framework</li>
                  <li>• <strong>Uvicorn:</strong> ASGI server for production</li>
                  <li>• <strong>Pydantic:</strong> Data validation and settings</li>
                  <li>• <strong>SQLAlchemy:</strong> ORM and database toolkit</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">ML/Data Science</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>XGBoost:</strong> Gradient boosting for stock screening</li>
                  <li>• <strong>JAX:</strong> High-performance ML framework</li>
                  <li>• <strong>Gymnasium:</strong> RL environment standard</li>
                  <li>• <strong>pandas/numpy:</strong> Data manipulation</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">External APIs</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>Schwab API:</strong> Trading and account data</li>
                  <li>• <strong>Alpha Vantage:</strong> Market data provider</li>
                  <li>• <strong>ngrok:</strong> OAuth callback tunneling</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">Utilities</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>python-dotenv:</strong> Environment management</li>
                  <li>• <strong>requests:</strong> HTTP client</li>
                  <li>• <strong>psycopg2:</strong> PostgreSQL adapter</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Frontend Technologies</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">React Ecosystem</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>Next.js 14:</strong> React framework with App Router</li>
                  <li>• <strong>React 18:</strong> UI library with hooks</li>
                  <li>• <strong>TypeScript:</strong> Type-safe development</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">Styling & UI</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>Tailwind CSS:</strong> Utility-first CSS framework</li>
                  <li>• <strong>lucide-react:</strong> Icon library</li>
                  <li>• <strong>Custom components:</strong> Reusable UI patterns</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">Data & State</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>axios:</strong> HTTP client for API calls</li>
                  <li>• <strong>React hooks:</strong> useState, useEffect for state</li>
                  <li>• <strong>Client-side rendering:</strong> 'use client' components</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-gray-800 mb-2">Development</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• <strong>ESLint:</strong> Code linting</li>
                  <li>• <strong>PostCSS:</strong> CSS processing</li>
                  <li>• <strong>Hot reload:</strong> Fast refresh during dev</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* File Structure */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Project Structure</h2>

        <div className="bg-gray-900 text-gray-100 p-6 rounded-lg font-mono text-sm not-prose mb-6">
          acis-ai-platform/<br/>
          ├── backend/                 # FastAPI backend<br/>
          │   ├── api/<br/>
          │   │   ├── routers/        # API route handlers<br/>
          │   │   ├── database/       # DB connection & models<br/>
          │   │   └── main.py         # FastAPI app entry point<br/>
          │   └── .env                # Environment variables<br/>
          ├── frontend/                # Next.js frontend<br/>
          │   ├── src/<br/>
          │   │   ├── app/            # App Router pages<br/>
          │   │   ├── components/     # React components<br/>
          │   │   ├── lib/            # Utilities (API client)<br/>
          │   │   └── types/          # TypeScript types<br/>
          │   └── package.json<br/>
          ├── ml_models/               # Trained XGBoost models<br/>
          │   └── growth_midcap_*.pkl<br/>
          ├── rl_models/               # Trained RL agents<br/>
          │   └── jax_ppo_*.pkl<br/>
          ├── rl_trading/              # RL training scripts<br/>
          │   ├── train_jax_ppo.py    # JAX PPO training<br/>
          │   └── hybrid_portfolio_env.py  # Gym environment<br/>
          ├── scripts/                 # Operational scripts<br/>
          │   ├── run_eod_pipeline.sh # Daily data load<br/>
          │   ├── auto_train_models.py # ML model training<br/>
          │   └── run_daily_rebalance.py<br/>
          ├── backtesting/             # Backtest framework<br/>
          │   └── autonomous_backtest.py<br/>
          ├── database/                # SQL schema & migrations<br/>
          │   ├── schema.sql<br/>
          │   └── initial_data.sql<br/>
          ├── logs/                    # Application logs<br/>
          └── requirements.txt         # Python dependencies
        </div>
      </section>

      {/* API Endpoints */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Core API Endpoints</h2>

        <div className="space-y-4 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">GET</span>
              <code className="text-sm font-mono text-gray-900">/api/clients/</code>
            </div>
            <p className="text-sm text-gray-600">List all clients with pagination</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">GET</span>
              <code className="text-sm font-mono text-gray-900">/api/schwab/portfolio/{"{client_id}"}</code>
            </div>
            <p className="text-sm text-gray-600">Get client's Schwab portfolio (positions + balances)</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">POST</span>
              <code className="text-sm font-mono text-gray-900">/api/trading/recommendations/generate</code>
            </div>
            <p className="text-sm text-gray-600">Generate ML+RL trade recommendations for rebalance</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">GET</span>
              <code className="text-sm font-mono text-gray-900">/api/autonomous/status</code>
            </div>
            <p className="text-sm text-gray-600">Get autonomous trading system status and metrics</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">POST</span>
              <code className="text-sm font-mono text-gray-900">/api/clients/{"{client_id}"}/sync-balance-from-schwab</code>
            </div>
            <p className="text-sm text-gray-600">Sync Schwab account balance to paper trading account</p>
          </div>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose mt-6">
          <p className="text-sm text-blue-800">
            <strong>Full API Reference:</strong> See <Link href="/docs/technical/api" className="underline">API Documentation</Link> for
            complete endpoint list with request/response schemas.
          </p>
        </div>
      </section>

      {/* Deployment */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Deployment</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 not-prose mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Production Deployment Checklist</h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>✓ Configure production database with backups</li>
            <li>✓ Set up SSL certificates for HTTPS</li>
            <li>✓ Use production-grade ASGI server (Uvicorn with Gunicorn)</li>
            <li>✓ Configure cron jobs for daily EOD pipeline and rebalancing</li>
            <li>✓ Set up monitoring (Prometheus, Grafana) for system health</li>
            <li>✓ Configure log rotation and archival</li>
            <li>✓ Use environment variables (not .env files) for secrets</li>
            <li>✓ Set up CI/CD pipeline for automated deployments</li>
          </ul>
        </div>

        <div className="bg-yellow-50 border-l-4 border-yellow-600 p-4 not-prose">
          <p className="text-sm font-medium text-yellow-900 mb-1">GPU Requirements</p>
          <p className="text-sm text-yellow-800">
            RL training requires NVIDIA GPU with CUDA 12.1+ support. For production deployments,
            consider cloud GPU instances (AWS p3, Google Cloud GPU) for monthly model retraining.
          </p>
        </div>
      </section>

      {/* Deep Dive Links */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Technical Deep Dives</h2>
        <div className="grid grid-cols-1 gap-4 not-prose">
          <Link href="/docs/technical/database" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Database Schema</h3>
            <p className="text-sm text-gray-600">Complete schema documentation with table relationships</p>
          </Link>

          <Link href="/docs/technical/api" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">API Reference</h3>
            <p className="text-sm text-gray-600">All endpoints with request/response examples</p>
          </Link>

          <Link href="/docs/technical/ml-models" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">ML Models</h3>
            <p className="text-sm text-gray-600">XGBoost model training, features, and inference</p>
          </Link>

          <Link href="/docs/technical/rl-training" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">RL Training</h3>
            <p className="text-sm text-gray-600">PPO agent training with JAX and Gymnasium</p>
          </Link>

          <Link href="/docs/technical/deployment" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Deployment Guide</h3>
            <p className="text-sm text-gray-600">Production deployment, scaling, and maintenance</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
