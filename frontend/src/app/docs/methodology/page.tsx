'use client'

import Link from 'next/link'
import { TrendingUp, Brain, Shield, Repeat } from 'lucide-react'

export default function MethodologyOverview() {
  return (
    <div className="prose prose-blue max-w-none">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">Methodology Overview</h1>
      <p className="text-xl text-gray-600 mb-8">
        Understanding the ACIS AI trading system's approach to autonomous portfolio management.
      </p>

      {/* Core Philosophy */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Core Philosophy</h2>
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6 not-prose mb-6">
          <p className="text-gray-800 leading-relaxed">
            ACIS AI combines the best of traditional quantitative finance with cutting-edge artificial intelligence.
            Rather than relying on a single strategy or model, the system employs a <strong>meta-learning approach</strong> that
            selects optimal strategies based on current market conditions, then uses reinforcement learning to
            optimize portfolio allocation within that strategy.
          </p>
        </div>

        <p className="mb-4">The system is built on three core principles:</p>
        <ol className="space-y-3">
          <li>
            <strong>Diversification Across Strategies:</strong> Multiple proven investment strategies
            (Growth, Momentum, Value, Dividend) ensure no single market regime causes catastrophic failure
          </li>
          <li>
            <strong>Adaptive Intelligence:</strong> Machine learning models continuously learn from market data,
            and meta-models select the best-performing strategy for current conditions
          </li>
          <li>
            <strong>Risk-First Design:</strong> Position limits, drift thresholds, and transaction costs are
            hard-coded constraints that AI must operate within
          </li>
        </ol>
      </section>

      {/* System Architecture */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Four-Layer Architecture</h2>

        <div className="grid grid-cols-1 gap-6 not-prose mb-8">
          {/* Layer 1 */}
          <div className="bg-white border-2 border-blue-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-blue-100 rounded-lg flex-shrink-0">
                <span className="text-2xl font-bold text-blue-600">1</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Market Regime Detection</h3>
                <p className="text-gray-600 mb-3">
                  Analyzes macro indicators (VIX, yields, sector rotation) to classify current market regime as
                  one of: Bull, Bear, High Volatility, Low Volatility, Sideways.
                </p>
                <div className="bg-blue-50 p-3 rounded text-sm text-gray-700">
                  <strong>Output:</strong> Market regime classification + confidence score
                </div>
              </div>
            </div>
          </div>

          {/* Layer 2 */}
          <div className="bg-white border-2 border-purple-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-purple-100 rounded-lg flex-shrink-0">
                <span className="text-2xl font-bold text-purple-600">2</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Meta-Model Strategy Selection</h3>
                <p className="text-gray-600 mb-3">
                  Given the market regime, selects which trading strategy (Growth/Momentum/Value/Dividend) and
                  market cap segment (Large/Mid/Small) is expected to perform best.
                </p>
                <div className="bg-purple-50 p-3 rounded text-sm text-gray-700">
                  <strong>Output:</strong> Selected strategy (e.g., "growth_largecap") + confidence
                </div>
              </div>
            </div>
          </div>

          {/* Layer 3 */}
          <div className="bg-white border-2 border-green-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-green-100 rounded-lg flex-shrink-0">
                <span className="text-2xl font-bold text-green-600">3</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">ML Stock Screening (XGBoost)</h3>
                <p className="text-gray-600 mb-3">
                  Strategy-specific XGBoost model evaluates ~2000 stocks based on fundamentals, technicals,
                  and risk metrics. Screens down to top 100 candidates with highest predicted returns.
                </p>
                <div className="bg-green-50 p-3 rounded text-sm text-gray-700">
                  <strong>Output:</strong> Top 100 stocks ranked by ML score (0-1)
                </div>
              </div>
            </div>
          </div>

          {/* Layer 4 */}
          <div className="bg-white border-2 border-orange-200 rounded-lg p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-orange-100 rounded-lg flex-shrink-0">
                <span className="text-2xl font-bold text-orange-600">4</span>
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">RL Portfolio Optimization (PPO)</h3>
                <p className="text-gray-600 mb-3">
                  Reinforcement learning agent (Proximal Policy Optimization) trained on 9 years of historical
                  data decides optimal portfolio weights across top 50 positions from ML candidates.
                </p>
                <div className="bg-orange-50 p-3 rounded text-sm text-gray-700">
                  <strong>Output:</strong> Portfolio weights for each position (target allocation percentages)
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 not-prose">
          <h4 className="font-semibold text-gray-900 mb-3">Why This Architecture?</h4>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>
              • <strong>Separation of Concerns:</strong> Each layer focuses on one task (regime detection, strategy selection,
              stock picking, portfolio optimization)
            </li>
            <li>
              • <strong>Hybrid ML+RL:</strong> ML excels at prediction (which stocks will perform), RL excels at sequential
              decision-making (how to allocate capital over time)
            </li>
            <li>
              • <strong>Scalability:</strong> Can train 12 independent models (4 strategies × 3 market caps) in parallel,
              each specialized for its domain
            </li>
          </ul>
        </div>
      </section>

      {/* Trading Strategies */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Trading Strategies</h2>
        <p className="mb-6">ACIS AI implements four fundamental investment strategies:</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 not-prose">
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <TrendingUp className="w-6 h-6 text-blue-600" />
              <h3 className="text-lg font-semibold text-gray-900">Growth</h3>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Focuses on companies with high revenue/earnings growth rates, strong gross margins, and
              expanding market share. Prioritizes future potential over current valuation.
            </p>
            <div className="text-xs text-gray-500">
              <strong>Key Metrics:</strong> Revenue growth, EPS growth, gross margin, R&D spending
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <Repeat className="w-6 h-6 text-purple-600" />
              <h3 className="text-lg font-semibold text-gray-900">Momentum</h3>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Captures stocks with strong price trends and positive technical indicators. Rides trends
              until momentum reverses. Works best in trending markets.
            </p>
            <div className="text-xs text-gray-500">
              <strong>Key Metrics:</strong> 50/200-day SMA, RSI, MACD, price momentum, volume trends
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <Shield className="w-6 h-6 text-green-600" />
              <h3 className="text-lg font-semibold text-gray-900">Value</h3>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Seeks undervalued companies trading below intrinsic value based on fundamentals.
              Emphasizes low P/E, P/B ratios and strong balance sheets.
            </p>
            <div className="text-xs text-gray-500">
              <strong>Key Metrics:</strong> P/E ratio, P/B ratio, dividend yield, debt/equity, ROE
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center gap-3 mb-3">
              <Brain className="w-6 h-6 text-orange-600" />
              <h3 className="text-lg font-semibold text-gray-900">Dividend</h3>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Targets stable, dividend-paying companies with consistent cash flow. Provides downside
              protection and income generation. Lower volatility than growth.
            </p>
            <div className="text-xs text-gray-500">
              <strong>Key Metrics:</strong> Dividend yield, payout ratio, dividend growth, FCF, stability
            </div>
          </div>
        </div>

        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose mt-6">
          <p className="text-sm text-blue-800">
            <strong>Market Cap Segments:</strong> Each strategy is further specialized by market capitalization
            (Large: &gt;$10B, Mid: $2-10B, Small: &lt;$2B), resulting in 12 total portfolio models.
          </p>
        </div>
      </section>

      {/* Risk Management */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Risk Management Framework</h2>
        <p className="mb-4">Built-in safeguards that AI must operate within:</p>

        <div className="space-y-4">
          <div className="bg-white border-l-4 border-red-600 p-4 not-prose">
            <h4 className="font-semibold text-gray-900 mb-2">Position Limits</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              <li>• <strong>Min Position:</strong> 1% of portfolio (prevents over-diversification)</li>
              <li>• <strong>Max Position:</strong> 10% of portfolio (prevents concentration risk)</li>
              <li>• <strong>Max Positions:</strong> 50 holdings (manageable complexity)</li>
            </ul>
          </div>

          <div className="bg-white border-l-4 border-orange-600 p-4 not-prose">
            <h4 className="font-semibold text-gray-900 mb-2">Drift Thresholds</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              <li>• <strong>Portfolio Drift:</strong> 5% deviation from target triggers rebalance</li>
              <li>• <strong>Position Drift:</strong> Individual positions that drift &gt;3% flagged for adjustment</li>
            </ul>
          </div>

          <div className="bg-white border-l-4 border-yellow-600 p-4 not-prose">
            <h4 className="font-semibold text-gray-900 mb-2">Transaction Costs</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              <li>• <strong>Commission:</strong> $0 (modern brokerages)</li>
              <li>• <strong>Slippage:</strong> 0.1% (market impact modeling)</li>
              <li>• <strong>Turnover Penalty:</strong> RL agent learns to minimize unnecessary trading</li>
            </ul>
          </div>

          <div className="bg-white border-l-4 border-green-600 p-4 not-prose">
            <h4 className="font-semibold text-gray-900 mb-2">Cash Reserves</h4>
            <ul className="space-y-1 text-sm text-gray-700">
              <li>• <strong>Minimum Cash:</strong> Configurable per client (default 2-5%)</li>
              <li>• <strong>Purpose:</strong> Handle withdrawals, fees, opportunity for new positions</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Backtesting & Validation */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Backtesting & Validation</h2>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 not-prose mb-6">
          <h4 className="font-semibold text-gray-900 mb-3">Train/Test Split Design</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-600 mb-1">Training Period</div>
              <div className="font-semibold text-gray-900">2015-2023 (9 years)</div>
              <div className="text-xs text-gray-500 mt-1">Used to train all ML and RL models</div>
            </div>
            <div>
              <div className="text-gray-600 mb-1">Test Period</div>
              <div className="font-semibold text-gray-900">2024-2025 (held out)</div>
              <div className="text-xs text-gray-500 mt-1">Out-of-sample validation, never seen during training</div>
            </div>
          </div>
        </div>

        <p className="mb-4">This approach prevents:</p>
        <ul className="space-y-2">
          <li><strong>Overfitting:</strong> Models can't memorize recent market patterns</li>
          <li><strong>Data Snooping:</strong> Test data completely isolated from training</li>
          <li><strong>Look-Ahead Bias:</strong> Models only use information available at decision time</li>
        </ul>

        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 not-prose mt-6">
          <p className="text-sm text-blue-800">
            Once models prove successful on 2024-2025 test data, they can be deployed for live trading.
            Models are retrained monthly on expanding window to incorporate new market data.
          </p>
        </div>
      </section>

      {/* Deep Dive Links */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Learn More</h2>
        <div className="grid grid-cols-1 gap-4 not-prose">
          <Link href="/docs/methodology/trading-strategies" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Trading Strategies in Detail</h3>
            <p className="text-sm text-gray-600">Deep dive into each strategy's features and when they work best</p>
          </Link>

          <Link href="/docs/methodology/hybrid-ml-rl" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Hybrid ML+RL Architecture</h3>
            <p className="text-sm text-gray-600">Technical details of XGBoost screening + PPO optimization</p>
          </Link>

          <Link href="/docs/methodology/risk-management" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Risk Management Framework</h3>
            <p className="text-sm text-gray-600">How constraints and safeguards protect client capital</p>
          </Link>

          <Link href="/docs/methodology/market-regime" className="block p-4 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 transition-colors">
            <h3 className="font-semibold text-gray-900 mb-1">Market Regime Detection</h3>
            <p className="text-sm text-gray-600">How the system identifies and adapts to changing market conditions</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
