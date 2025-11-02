'use client'
import Link from 'next/link'
import { Brain, Target, ArrowRight } from 'lucide-react'

export default function HybridMlRl() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Hybrid ML+RL System</h1>
      <p className="text-xl text-gray-600 mb-8">XGBoost and PPO agents work together for optimal portfolio construction.</p>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Two-Stage Architecture</h2>
        <div className="grid grid-cols-2 gap-4 not-prose">
          <div className="bg-white border p-4 rounded">
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold">Stage 1: ML Screening</h3>
            </div>
            <p className="text-sm mb-2">XGBoost narrows 2000+ stocks to top 100 candidates</p>
            <div className="bg-gray-50 p-2 rounded text-xs">
              <p><strong>Input:</strong> 50+ features per stock</p>
              <p><strong>Output:</strong> Ranked list of 100 stocks</p>
              <p><strong>Time:</strong> ~10 seconds</p>
            </div>
          </div>
          <div className="bg-white border p-4 rounded">
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5 text-purple-600" />
              <h3 className="font-semibold">Stage 2: RL Optimization</h3>
            </div>
            <p className="text-sm mb-2">PPO agent optimizes weights for top 50 positions</p>
            <div className="bg-gray-50 p-2 rounded text-xs">
              <p><strong>Input:</strong> Top 100 from ML</p>
              <p><strong>Output:</strong> Portfolio with optimal allocations</p>
              <p><strong>Time:</strong> ~20-30 seconds</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Why Hybrid?</h2>
        <p className="text-sm">Combining ML and RL leverages strengths of both approaches:</p>
        <div className="space-y-2 mt-3 not-prose text-sm">
          <div className="bg-blue-50 p-3 rounded">
            <strong>ML Strengths:</strong> Fast screening, interpretable features, handles large universes efficiently
          </div>
          <div className="bg-purple-50 p-3 rounded">
            <strong>RL Strengths:</strong> Multi-period optimization, risk-adjusted allocation, learns from market feedback
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Training Process</h2>
        <div className="bg-gray-900 text-gray-100 p-3 rounded font-mono text-xs not-prose">
          # Train ML model (weekly)<br/>
          python ml_models/incremental_train_xgboost.py --strategy growth --market-cap mid<br/><br/>
          # Train RL agent (monthly)<br/>
          python rl_trading/incremental_train_ppo.py --strategy growth --market-cap mid
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Related Docs</h2>
        <div className="grid grid-cols-2 gap-3 not-prose">
          <Link href="/docs/technical/ml-models" className="block p-3 bg-white border-2 rounded hover:border-blue-500">
            <h3 className="font-semibold text-sm">ML Models Details</h3>
          </Link>
          <Link href="/docs/technical/rl-training" className="block p-3 bg-white border-2 rounded hover:border-blue-500">
            <h3 className="font-semibold text-sm">RL Training Details</h3>
          </Link>
        </div>
      </section>
    </div>
  )
}
