'use client';

import React, { useState, useEffect } from 'react';

interface Portfolio {
  ticker: string;
  predicted_return: number;
  target_weight: number;
}

interface PredictionStats {
  total_universe: number;
  top_predicted_return: number;
  median_predicted_return: number;
  model_ic: number;
  last_updated: string;
}

export default function MLPortfolioPage() {
  const [portfolio, setPortfolio] = useState<Portfolio[]>([]);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [stats, setStats] = useState<PredictionStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('portfolio');
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [config, setConfig] = useState({
    top_n: 50,
    weighting: 'signal',
    max_position: 0.10,
    cash_available: 100000,
    min_market_cap: 2000000000,  // Default: $2B (mid-cap+)
    strategy: 'growth',  // 'dividend', 'growth', 'value'
    market_cap_segment: 'mid'  // 'small', 'mid', 'large', 'all'
  });

  const loadPortfolio = async () => {
    console.log('🚀 loadPortfolio called with config:', config);
    setLoading(true);
    try {
      console.log('📡 Fetching from API...');
      const response = await fetch('/api/ml-portfolio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      console.log('✅ Response received:', response.status);
      const data = await response.json();
      console.log('📊 Data received:', data);

      setPortfolio(data.target_portfolio || []);
      setPredictions(data.predictions || []);
      setStats(data.stats || null);
      console.log('✅ Portfolio set! Length:', data.target_portfolio?.length);
    } catch (error) {
      console.error('❌ Error loading portfolio:', error);
      alert('Error loading portfolio: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Remove auto-load on mount - user must click "Generate Portfolio" button
  // useEffect(() => {
  //   loadPortfolio();
  // }, []);

  const formatPercent = (value: number) => {
    return (value * 100).toFixed(2) + '%';
  };

  const formatCurrency = (value: number) => {
    return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Deprecation Notice */}
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong className="font-medium">Legacy Page:</strong> This manual ML portfolio generator has been superseded by the{' '}
              <a href="/autonomous" className="underline hover:text-yellow-900">Autonomous Trading System</a>, which automatically
              selects strategies based on market regime and combines XGBoost + PPO RL models. Use this page for manual testing or
              insights into individual strategy models.
            </p>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">ML Portfolio Manager (Legacy)</h1>
          <p className="text-gray-600 mt-1">
            XGBoost predictions with IC: 0.0876
          </p>
        </div>
        <button
          onClick={loadPortfolio}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Generate Portfolio
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Universe Size</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.total_universe}</p>
            <p className="text-xs text-gray-500 mt-1">stocks analyzed</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Top Prediction</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{formatPercent(stats.top_predicted_return)}</p>
            <p className="text-xs text-gray-500 mt-1">best stock forecast</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Model IC</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.model_ic.toFixed(4)}</p>
            <p className="text-xs text-gray-500 mt-1">Spearman correlation</p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-gray-600">Portfolio Value</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(config.cash_available)}</p>
            <p className="text-xs text-gray-500 mt-1">{portfolio.length} positions</p>
          </div>
        </div>
      )}

      {/* Configuration */}
      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Configuration</h3>

        {/* Strategy Selection Row */}
        <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-gray-200">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Investment Strategy</label>
            <select
              value={config.strategy}
              onChange={(e) => setConfig({...config, strategy: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="dividend">Dividend (High Income)</option>
              <option value="growth">Growth (High Appreciation)</option>
              <option value="value">Value (Undervalued Quality)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {config.strategy === 'dividend' && 'Focus: Sustainable high dividends + moderate growth'}
              {config.strategy === 'growth' && 'Focus: High price appreciation potential'}
              {config.strategy === 'value' && 'Focus: Undervalued stocks + mean reversion'}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Market Cap Segment</label>
            <select
              value={config.market_cap_segment}
              onChange={(e) => {
                const segment = e.target.value;
                setConfig({...config, market_cap_segment: segment});
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={config.strategy === 'dividend'}
            >
              {config.strategy === 'dividend' ? (
                <option value="mid">Mid/Large Cap Only</option>
              ) : (
                <>
                  <option value="small">Small Cap ($300M-$2B, price &gt;$5)</option>
                  <option value="mid">Mid Cap ($2B-$10B)</option>
                  <option value="large">Large Cap (&gt;$10B)</option>
                  <option value="all">All Caps (&gt;$300M, price &gt;$5)</option>
                </>
              )}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {config.strategy === 'dividend' ? 'Dividend strategy uses mid/large cap only' : 'Model trained on this market cap segment'}
            </p>
          </div>
        </div>

        {/* Portfolio Settings Row */}
        <div className="grid grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Number of Stocks</label>
            <input
              type="number"
              value={config.top_n}
              onChange={(e) => setConfig({...config, top_n: parseInt(e.target.value)})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="10"
              max="200"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Market Cap Filter</label>
            <select
              value={config.min_market_cap}
              onChange={(e) => setConfig({...config, min_market_cap: parseFloat(e.target.value)})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={0}>All Stocks</option>
              <option value={300000000}>Small+ (&gt;$300M)</option>
              <option value={2000000000}>Mid+ (&gt;$2B)</option>
              <option value={10000000000}>Large+ (&gt;$10B)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Weighting</label>
            <select
              value={config.weighting}
              onChange={(e) => setConfig({...config, weighting: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="equal">Equal Weight</option>
              <option value="rank">Rank Weight</option>
              <option value="signal">Signal Weight</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Position (%)</label>
            <input
              type="number"
              value={config.max_position * 100}
              onChange={(e) => setConfig({...config, max_position: parseFloat(e.target.value) / 100})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="1"
              max="20"
              step="0.5"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cash Available</label>
            <input
              type="number"
              value={config.cash_available}
              onChange={(e) => setConfig({...config, cash_available: parseFloat(e.target.value)})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              min="1000"
              step="1000"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow border border-gray-200">
        <div className="border-b border-gray-200">
          <div className="flex space-x-8 px-6">
            {['portfolio', 'predictions', 'performance'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab === 'portfolio' && 'Target Portfolio'}
                {tab === 'predictions' && 'All Predictions'}
                {tab === 'performance' && 'Performance'}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6">
          {/* Target Portfolio Tab */}
          {activeTab === 'portfolio' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Target Portfolio ({portfolio.length} positions)
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Predicted Return</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target Weight</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Position Value</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {portfolio.slice(0, 20).map((position, index) => (
                      <tr key={position.ticker} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{index + 1}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-600">
                          <button
                            onClick={() => setSelectedTicker(position.ticker)}
                            className="hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
                          >
                            {position.ticker}
                          </button>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${
                            position.predicted_return > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {formatPercent(position.predicted_return)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatPercent(position.target_weight)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatCurrency(position.target_weight * config.cash_available)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {portfolio.length > 20 && (
                <p className="text-center mt-4 text-sm text-gray-500">
                  Showing top 20 of {portfolio.length} positions
                </p>
              )}
            </div>
          )}

          {/* All Predictions Tab */}
          {activeTab === 'predictions' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                All Predictions
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Rank</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ticker</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Predicted Return</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">In Portfolio</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {predictions.slice(0, 50).map((pred) => (
                      <tr key={pred.ticker} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{pred.rank}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-600">
                          <button
                            onClick={() => setSelectedTicker(pred.ticker)}
                            className="hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
                          >
                            {pred.ticker}
                          </button>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${
                            pred.predicted_return > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {formatPercent(pred.predicted_return)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {portfolio.find(p => p.ticker === pred.ticker) ? '✓' : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {predictions.length > 50 && (
                <p className="text-center mt-4 text-sm text-gray-500">
                  Showing top 50 of {predictions.length} predictions
                </p>
              )}
            </div>
          )}

          {/* Performance Tab */}
          {activeTab === 'performance' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Model Performance
              </h3>
              <div className="space-y-6">
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Spearman IC</p>
                    <p className="text-2xl font-bold text-gray-900">0.0876</p>
                    <p className="text-xs text-green-600 mt-1">Excellent for stock prediction</p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Training Period</p>
                    <p className="text-2xl font-bold text-gray-900">10.8 years</p>
                    <p className="text-xs text-gray-600 mt-1">2015-2025</p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Features</p>
                    <p className="text-2xl font-bold text-gray-900">51</p>
                    <p className="text-xs text-gray-600 mt-1">technical + fundamental</p>
                  </div>
                </div>

                <div className="border-t border-gray-200 pt-4">
                  <h4 className="font-semibold text-gray-900 mb-3">Top Features (by importance)</h4>
                  <div className="space-y-2">
                    {[
                      { name: 'MACD Value', importance: '34.3%' },
                      { name: '5-day Return', importance: '8.4%' },
                      { name: 'Signal Value', importance: '8.2%' },
                      { name: 'Volume Ratio', importance: '7.6%' }
                    ].map((feature) => (
                      <div key={feature.name} className="flex justify-between items-center py-2 px-3 bg-gray-50 rounded">
                        <span className="text-sm text-gray-700">{feature.name}</span>
                        <span className="text-sm font-semibold text-blue-600">{feature.importance}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Yahoo Finance Modal */}
      {selectedTicker && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex justify-between items-center px-6 py-4 border-b border-gray-200">
              <h3 className="text-xl font-bold text-gray-900">{selectedTicker} - Yahoo Finance</h3>
              <button
                onClick={() => setSelectedTicker(null)}
                className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded p-1"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              {/* Quick Links */}
              <div className="flex gap-2 mb-4">
                <a
                  href={`https://finance.yahoo.com/quote/${selectedTicker}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 text-sm font-medium"
                >
                  Open Yahoo Finance
                </a>
                <a
                  href={`https://finance.yahoo.com/quote/${selectedTicker}/key-statistics`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
                >
                  Statistics
                </a>
                <a
                  href={`https://finance.yahoo.com/quote/${selectedTicker}/analysis`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-medium"
                >
                  Analysis
                </a>
              </div>

              {/* TradingView Widget (more reliable than Yahoo Finance embed) */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <iframe
                  src={`https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=${selectedTicker}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Etc%2FUTC&withdateranges=1&studies_overrides={}&overrides={}&enabled_features=[]&disabled_features=[]&locale=en&utm_source=localhost&utm_medium=widget_new&utm_campaign=chart&utm_term=${selectedTicker}`}
                  className="w-full h-[500px] border-0"
                  title={`${selectedTicker} Chart`}
                />
              </div>

              {/* Additional Info Section */}
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">Quick Info</h4>
                  <div className="space-y-1 text-sm">
                    <p className="text-gray-600">
                      <a
                        href={`https://stockanalysis.com/stocks/${selectedTicker.toLowerCase()}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        View on Stock Analysis →
                      </a>
                    </p>
                    <p className="text-gray-600">
                      <a
                        href={`https://www.marketwatch.com/investing/stock/${selectedTicker.toLowerCase()}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        View on MarketWatch →
                      </a>
                    </p>
                  </div>
                </div>

                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">Portfolio Info</h4>
                  <div className="space-y-1 text-sm text-gray-600">
                    {portfolio.find(p => p.ticker === selectedTicker) ? (
                      <>
                        <p>✓ In target portfolio</p>
                        <p>Predicted Return: {formatPercent(portfolio.find(p => p.ticker === selectedTicker)!.predicted_return)}</p>
                        <p>Target Weight: {formatPercent(portfolio.find(p => p.ticker === selectedTicker)!.target_weight)}</p>
                      </>
                    ) : (
                      <p>Not in target portfolio</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
