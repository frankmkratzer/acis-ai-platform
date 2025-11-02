'use client';

import { useState, useEffect } from 'react';

interface ModelInfo {
  name: string;
  path: string;
  created: string;
  size_mb: number;
  spearman_ic: number | null;
  n_features: number | null;
  framework: string | null;
}

interface TrainingJob {
  job_id: string;
  status: string;
  framework: string;
  started_at: string;
  log_file: string;
}

interface FeatureImportance {
  feature: string;
  importance: number;
}

export default function MLModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelDetails, setModelDetails] = useState<any>(null);
  const [jobLogs, setJobLogs] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [showTrainForm, setShowTrainForm] = useState(false);

  const [trainConfig, setTrainConfig] = useState({
    framework: 'xgboost',  // 'xgboost' or 'rl_ppo'
    start_date: '2015-01-01',
    end_date: '2025-10-30',
    gpu: true,
    strategy: 'growth',  // 'dividend', 'growth', 'value'
    market_cap_segment: 'mid',  // 'small', 'mid', 'large', 'all'
    // RL-specific parameters
    timesteps: 1000000,
    eval_freq: 10000,
    save_freq: 50000
  });

  // Load models on mount
  useEffect(() => {
    loadModels();
    loadJobs();
  }, []);

  const loadModels = async () => {
    try {
      const response = await fetch('/api/ml-models/list');
      const data = await response.json();
      setModels(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error loading models:', error);
      setModels([]);
    }
  };

  const loadJobs = async () => {
    try {
      const response = await fetch('/api/ml-models/jobs');
      const data = await response.json();
      setJobs(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error loading jobs:', error);
      setJobs([]);
    }
  };

  const loadModelDetails = async (modelName: string) => {
    try {
      const response = await fetch(`/api/ml-models/${modelName}/details`);
      const data = await response.json();
      setModelDetails(data);
      setSelectedModel(modelName);
    } catch (error) {
      console.error('Error loading model details:', error);
    }
  };

  const deleteModel = async (modelName: string) => {
    if (!confirm(`Are you sure you want to delete model "${modelName}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/ml-models/${modelName}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        alert('Model deleted successfully');
        loadModels();
        if (selectedModel === modelName) {
          setSelectedModel(null);
          setModelDetails(null);
        }
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error deleting model:', error);
      alert('Error deleting model');
    }
  };

  const startTraining = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/ml-models/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trainConfig)
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Training job started: ${data.job_id}`);
        setShowTrainForm(false);
        loadJobs();
      } else {
        alert(`Error: ${data.error || 'Failed to start training'}`);
      }
    } catch (error) {
      console.error('Error starting training:', error);
      alert('Error starting training job');
    } finally {
      setLoading(false);
    }
  };

  const loadJobLogs = async (jobId: string) => {
    try {
      const response = await fetch(`/api/ml-models/jobs/${jobId}/logs?lines=100`);
      const data = await response.json();
      setJobLogs(data.logs);
    } catch (error) {
      console.error('Error loading logs:', error);
    }
  };

  const deleteJob = async (jobId: string) => {
    if (!confirm(`Are you sure you want to delete training job "${jobId}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/ml-models/jobs/${jobId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        alert('Training job deleted successfully');
        loadJobs();
        setJobLogs('');
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to delete job'}`);
      }
    } catch (error) {
      console.error('Error deleting job:', error);
      alert('Error deleting training job');
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Deprecation Notice */}
        <div className="bg-yellow-900 border-l-4 border-yellow-400 p-4 rounded-lg mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-100">
                <strong className="font-medium">Legacy Page:</strong> This model training interface remains available for
                retraining the XGBoost and PPO models used by the{' '}
                <a href="/autonomous" className="underline hover:text-yellow-300">Autonomous Trading System</a>.
                Models are now automatically used by the autonomous system based on market regime.
              </p>
            </div>
          </div>
        </div>

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">ML Model Management</h1>
          <button
            onClick={() => setShowTrainForm(!showTrainForm)}
            title="Start training a new XGBoost ML model or PPO RL agent for stock selection and portfolio allocation"
            className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg font-semibold"
          >
            {showTrainForm ? 'Cancel' : 'Train New Model'}
          </button>
        </div>

        {/* Training Form */}
        {showTrainForm && (
          <div className="bg-gray-800 p-6 rounded-lg mb-8">
            <h2 className="text-xl font-bold mb-4">Train New Model</h2>

            {/* Framework Selection */}
            <div className="mb-4 pb-4 border-b border-gray-700">
              <label className="block text-sm mb-2 text-gray-300 font-semibold">Training Framework</label>
              <div className="flex gap-4">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    value="xgboost"
                    checked={trainConfig.framework === 'xgboost'}
                    onChange={(e) => setTrainConfig({...trainConfig, framework: e.target.value})}
                    className="mr-2"
                  />
                  <span className="text-sm">XGBoost (ML) - Stock Selection</span>
                </label>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    value="rl_ppo"
                    checked={trainConfig.framework === 'rl_ppo'}
                    onChange={(e) => setTrainConfig({...trainConfig, framework: e.target.value})}
                    className="mr-2"
                  />
                  <span className="text-sm">PPO (RL) - Portfolio Allocation</span>
                </label>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {trainConfig.framework === 'xgboost' && 'Train ML model to predict stock returns (20-day forward)'}
                {trainConfig.framework === 'rl_ppo' && 'Train RL agent to optimize portfolio weights using ML predictions'}
              </p>
            </div>

            {/* Strategy Selection */}
            <div className="grid grid-cols-2 gap-4 mb-4 pb-4 border-b border-gray-700">
              <div>
                <label className="block text-sm mb-2 text-gray-300">Investment Strategy</label>
                <select
                  value={trainConfig.strategy}
                  onChange={(e) => setTrainConfig({...trainConfig, strategy: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                >
                  <option value="dividend">Dividend (High Income)</option>
                  <option value="growth">Growth (High Appreciation)</option>
                  <option value="value">Value (Undervalued Quality)</option>
                </select>
                <p className="text-xs text-gray-400 mt-1">
                  {trainConfig.strategy === 'dividend' && 'Mid/Large cap (>$2B), price >$5, dividend yield >1%'}
                  {trainConfig.strategy === 'growth' && 'Focus on momentum + growth metrics'}
                  {trainConfig.strategy === 'value' && 'Focus on valuation multiples + fundamentals'}
                </p>
              </div>

              <div>
                <label className="block text-sm mb-2 text-gray-300">Market Cap Segment</label>
                <select
                  value={trainConfig.market_cap_segment}
                  onChange={(e) => setTrainConfig({...trainConfig, market_cap_segment: e.target.value})}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  disabled={trainConfig.strategy === 'dividend'}
                >
                  {trainConfig.strategy === 'dividend' ? (
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
                <p className="text-xs text-gray-400 mt-1">
                  Model will be trained on this segment
                </p>
              </div>
            </div>

            {/* Training Parameters */}
            <div className="grid grid-cols-3 gap-4 mb-4">
              {trainConfig.framework === 'xgboost' ? (
                <>
                  <div>
                    <label className="block text-sm mb-2 text-gray-300">GPU Acceleration</label>
                    <div className="flex items-center mt-3">
                      <input
                        type="checkbox"
                        checked={trainConfig.gpu}
                        onChange={(e) => setTrainConfig({...trainConfig, gpu: e.target.checked})}
                        className="mr-2"
                      />
                      <span className="text-sm">Enable GPU (CUDA)</span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm mb-2 text-gray-300">Start Date</label>
                    <input
                      type="date"
                      value={trainConfig.start_date}
                      onChange={(e) => setTrainConfig({...trainConfig, start_date: e.target.value})}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm mb-2 text-gray-300">End Date</label>
                    <input
                      type="date"
                      value={trainConfig.end_date}
                      onChange={(e) => setTrainConfig({...trainConfig, end_date: e.target.value})}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="block text-sm mb-2 text-gray-300">Training Timesteps</label>
                    <input
                      type="number"
                      value={trainConfig.timesteps}
                      onChange={(e) => setTrainConfig({...trainConfig, timesteps: parseInt(e.target.value)})}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      step="100000"
                    />
                    <p className="text-xs text-gray-400 mt-1">Total training steps (default: 1M)</p>
                  </div>

                  <div>
                    <label className="block text-sm mb-2 text-gray-300">Eval Frequency</label>
                    <input
                      type="number"
                      value={trainConfig.eval_freq}
                      onChange={(e) => setTrainConfig({...trainConfig, eval_freq: parseInt(e.target.value)})}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      step="1000"
                    />
                    <p className="text-xs text-gray-400 mt-1">Steps between evaluations</p>
                  </div>

                  <div>
                    <label className="block text-sm mb-2 text-gray-300">Save Frequency</label>
                    <input
                      type="number"
                      value={trainConfig.save_freq}
                      onChange={(e) => setTrainConfig({...trainConfig, save_freq: parseInt(e.target.value)})}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      step="10000"
                    />
                    <p className="text-xs text-gray-400 mt-1">Steps between checkpoints</p>
                  </div>

                  <div className="col-span-3">
                    <label className="block text-sm mb-2 text-gray-300">Device</label>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={trainConfig.gpu}
                        onChange={(e) => setTrainConfig({...trainConfig, gpu: e.target.checked})}
                        className="mr-2"
                      />
                      <span className="text-sm">Use GPU (CUDA)</span>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="flex items-center gap-4">
              <button
                onClick={startTraining}
                disabled={loading}
                title={`Start training job for ${trainConfig.framework === 'rl_ppo' ? 'RL PPO' : 'XGBoost'} model. Job will run in background and model will be saved when complete.`}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-6 py-2 rounded-lg font-semibold"
              >
                {loading ? 'Starting...' : `Train ${trainConfig.framework === 'rl_ppo' ? 'RL' : 'ML'} ${trainConfig.strategy.charAt(0).toUpperCase() + trainConfig.strategy.slice(1)} Model`}
              </button>
              <p className="text-sm text-gray-400">
                Model will be saved as: {trainConfig.framework === 'rl_ppo' ? 'ppo_hybrid_' : ''}{trainConfig.strategy}_{trainConfig.strategy === 'dividend' ? 'strategy' : `${trainConfig.market_cap_segment}cap`}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-8">
          {/* Models List */}
          <div>
            <h2 className="text-2xl font-bold mb-4">Trained Models ({models?.length || 0})</h2>

            <div className="space-y-4">
              {Array.isArray(models) && models.map((model) => (
                <div
                  key={model.name}
                  className="bg-gray-800 p-4 rounded-lg hover:bg-gray-750 cursor-pointer border-2 border-transparent hover:border-blue-600"
                  onClick={() => loadModelDetails(model.name)}
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-bold">{model.name}</h3>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteModel(model.name);
                      }}
                      title="Permanently delete this model file from disk. This action cannot be undone."
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Delete
                    </button>
                  </div>

                  <div className="text-sm space-y-1 text-gray-300">
                    <div>Framework: {model.framework || 'Unknown'}</div>
                    <div>Spearman IC: {model.spearman_ic ? model.spearman_ic.toFixed(4) : 'N/A'}</div>
                    <div>Features: {model.n_features || 'N/A'}</div>
                    <div>Size: {model.size_mb.toFixed(2)} MB</div>
                    <div>Created: {new Date(model.created).toLocaleString()}</div>
                  </div>
                </div>
              ))}

              {(!models || models.length === 0) && (
                <div className="bg-gray-800 p-8 rounded-lg text-center text-gray-400">
                  No models found. Train a new model to get started.
                </div>
              )}
            </div>
          </div>

          {/* Model Details / Training Jobs */}
          <div>
            {selectedModel && modelDetails ? (
              <div>
                <h2 className="text-2xl font-bold mb-4">Model Details: {selectedModel}</h2>

                <div className="bg-gray-800 p-6 rounded-lg mb-4">
                  <h3 className="text-lg font-bold mb-3">Metadata</h3>
                  <div className="space-y-2 text-sm">
                    <div className="grid grid-cols-2">
                      <span className="text-gray-400">Spearman IC:</span>
                      <span>{modelDetails.metadata.spearman_ic?.toFixed(4) || 'N/A'}</span>
                    </div>
                    <div className="grid grid-cols-2">
                      <span className="text-gray-400">Features:</span>
                      <span>{modelDetails.metadata.n_features || 'N/A'}</span>
                    </div>
                    <div className="grid grid-cols-2">
                      <span className="text-gray-400">Framework:</span>
                      <span>{modelDetails.metadata.framework || 'Unknown'}</span>
                    </div>
                    <div className="grid grid-cols-2">
                      <span className="text-gray-400">Size:</span>
                      <span>{modelDetails.size_mb.toFixed(2)} MB</span>
                    </div>
                  </div>
                </div>

                {modelDetails.feature_importance && modelDetails.feature_importance.length > 0 && (
                  <div className="bg-gray-800 p-6 rounded-lg">
                    <h3 className="text-lg font-bold mb-3">Top 20 Features</h3>
                    <div className="space-y-2 text-sm">
                      {modelDetails.feature_importance.map((feat: FeatureImportance, idx: number) => (
                        <div key={idx} className="flex items-center">
                          <span className="w-48 text-gray-400">{feat.feature}</span>
                          <div className="flex-1 bg-gray-700 rounded-full h-4 mx-2">
                            <div
                              className="bg-blue-600 h-4 rounded-full"
                              style={{
                                width: `${(feat.importance / modelDetails.feature_importance[0].importance) * 100}%`
                              }}
                            />
                          </div>
                          <span className="w-16 text-right">{feat.importance.toFixed(4)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div>
                <h2 className="text-2xl font-bold mb-4">Training Jobs ({jobs?.length || 0})</h2>

                <div className="space-y-4">
                  {Array.isArray(jobs) && jobs.map((job) => (
                    <div key={job.job_id} className="bg-gray-800 p-4 rounded-lg">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="text-lg font-bold">Job {job.job_id}</h3>
                          <div className="text-sm text-gray-400">
                            Framework: {job.framework}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
                            job.status === 'completed' ? 'bg-green-600' :
                            job.status === 'running' ? 'bg-blue-600' :
                            job.status === 'failed' ? 'bg-red-600' :
                            'bg-gray-600'
                          }`}>
                            {job.status}
                          </div>
                          <button
                            onClick={() => deleteJob(job.job_id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                            title="Delete job"
                          >
                            Delete
                          </button>
                        </div>
                      </div>

                      <div className="text-sm text-gray-400 mb-2">
                        Started: {new Date(job.started_at).toLocaleString()}
                      </div>

                      {job.log_file && (
                        <button
                          onClick={() => loadJobLogs(job.job_id)}
                          title="View the last 100 lines of training logs for this job"
                          className="text-blue-400 hover:text-blue-300 text-sm"
                        >
                          View Logs
                        </button>
                      )}
                    </div>
                  ))}

                  {(!jobs || jobs.length === 0) && (
                    <div className="bg-gray-800 p-8 rounded-lg text-center text-gray-400">
                      No training jobs yet
                    </div>
                  )}
                </div>

                {jobLogs && (
                  <div className="mt-4 bg-gray-800 p-4 rounded-lg">
                    <h3 className="text-lg font-bold mb-2">Recent Logs</h3>
                    <pre className="bg-black p-4 rounded text-xs overflow-x-auto max-h-96 overflow-y-auto">
                      {jobLogs}
                    </pre>
                    <button
                      onClick={() => setJobLogs('')}
                      className="mt-2 text-sm text-gray-400 hover:text-white"
                    >
                      Close Logs
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
