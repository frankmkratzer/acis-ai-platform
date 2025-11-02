'use client'

import { useState, useEffect } from 'react'
import {
  Play,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Database,
  HardDrive,
  Cpu,
  Activity
} from 'lucide-react'
import InlineHelp from '@/components/InlineHelp'
import Tooltip from '@/components/Tooltip'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface PipelineJob {
  job_id: string
  pipeline_type: 'daily' | 'weekly_ml' | 'monthly_rl'
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string | null
  completed_at: string | null
  log_file: string | null
  error_message: string | null
}

interface SystemStatus {
  status: string
  database_connected: boolean
  disk_usage_percent: number
  memory_usage_percent: number
  cpu_usage_percent: number
  active_pipelines: number
  recent_logs: string[]
}

export default function SystemAdminPage() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [jobs, setJobs] = useState<PipelineJob[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [runningPipelines, setRunningPipelines] = useState<Set<string>>(new Set())

  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/system/status`)
      if (response.ok) {
        const data = await response.json()
        setSystemStatus(data)
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error)
    }
  }

  // Fetch pipeline jobs
  const fetchJobs = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/pipelines/list?limit=20`)
      if (response.ok) {
        const data = await response.json()
        setJobs(data)

        // Track running pipelines
        const running = new Set(
          data
            .filter((job: PipelineJob) => job.status === 'running')
            .map((job: PipelineJob) => job.pipeline_type)
        )
        setRunningPipelines(running)
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    }
  }

  // Refresh all data
  const refreshData = async () => {
    setIsRefreshing(true)
    await Promise.all([fetchSystemStatus(), fetchJobs()])
    setIsRefreshing(false)
  }

  // Initial load
  useEffect(() => {
    refreshData()

    // Auto-refresh every 10 seconds
    const interval = setInterval(refreshData, 10000)
    return () => clearInterval(interval)
  }, [])

  // Run pipeline
  const runPipeline = async (pipelineType: 'daily' | 'weekly-ml' | 'monthly-rl') => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/pipelines/${pipelineType}`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        alert(`${pipelineType} pipeline started successfully!`)
        refreshData()
      } else {
        const error = await response.json()
        alert(`Failed to start pipeline: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Error starting pipeline: ${error}`)
    }
  }

  const formatDuration = (startedAt: string | null, completedAt: string | null) => {
    if (!startedAt) return '-'
    const start = new Date(startedAt)
    const end = completedAt ? new Date(completedAt) : new Date()
    const durationMs = end.getTime() - start.getTime()
    const minutes = Math.floor(durationMs / 60000)
    const seconds = Math.floor((durationMs % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }

  const getStatusColor = (percent: number, reverse = false) => {
    if (reverse) {
      if (percent < 50) return 'text-green-600'
      if (percent < 80) return 'text-yellow-600'
      return 'text-red-600'
    } else {
      if (percent < 50) return 'text-red-600'
      if (percent < 80) return 'text-yellow-600'
      return 'text-green-600'
    }
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Administration</h1>
          <p className="mt-2 text-gray-600">
            Manage data pipelines, training schedules, and system health
          </p>
        </div>

        <button
          onClick={refreshData}
          disabled={isRefreshing}
          title="Manually refresh system status and pipeline job history. Auto-refreshes every 10 seconds."
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* System Health Overview */}
      {systemStatus && (
        <div className="mb-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div
            className="bg-white rounded-lg shadow p-6"
            title="PostgreSQL database connection status. All market data, client information, and trading history is stored here."
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Database</span>
              <Database className={`w-5 h-5 ${systemStatus.database_connected ? 'text-green-600' : 'text-red-600'}`} />
            </div>
            <p className={`text-2xl font-bold ${systemStatus.database_connected ? 'text-green-600' : 'text-red-600'}`}>
              {systemStatus.database_connected ? 'Connected' : 'Disconnected'}
            </p>
          </div>

          <div
            className="bg-white rounded-lg shadow p-6"
            title="Server disk usage percentage. High usage (>80%) may impact performance and pipeline execution."
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Disk Usage</span>
              <HardDrive className={`w-5 h-5 ${getStatusColor(systemStatus.disk_usage_percent, true)}`} />
            </div>
            <p className={`text-2xl font-bold ${getStatusColor(systemStatus.disk_usage_percent, true)}`}>
              {systemStatus.disk_usage_percent.toFixed(1)}%
            </p>
          </div>

          <div
            className="bg-white rounded-lg shadow p-6"
            title="Server RAM usage. ML and RL training require significant memory. High usage (>80%) may slow training."
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Memory Usage</span>
              <Cpu className={`w-5 h-5 ${getStatusColor(systemStatus.memory_usage_percent, true)}`} />
            </div>
            <p className={`text-2xl font-bold ${getStatusColor(systemStatus.memory_usage_percent, true)}`}>
              {systemStatus.memory_usage_percent.toFixed(1)}%
            </p>
          </div>

          <div
            className="bg-white rounded-lg shadow p-6"
            title="Number of pipelines currently running. Only one instance of each pipeline type can run at a time."
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Active Pipelines</span>
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-blue-600">
              {systemStatus.active_pipelines}
            </p>
          </div>
        </div>
      )}

      {/* Pipeline Information */}
      <InlineHelp
        title="About Data Pipelines & Training Schedules"
        variant="info"
        learnMoreLink="/docs/operations"
        content={
          <div className="space-y-3">
            <p>
              The ACIS AI platform uses a three-tier pipeline schedule optimized for performance:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Daily Pipeline (~5 min):</strong> Refreshes data and materialized views.
                Runs automatically every evening.
              </li>
              <li>
                <strong>Weekly ML Training (~30-60 min):</strong> Retrains XGBoost models for stock screening.
                Runs automatically every Sunday.
              </li>
              <li>
                <strong>Monthly RL Training (~2-4 hrs):</strong> Retrains PPO agents for portfolio optimization.
                Runs automatically on the 1st of each month.
              </li>
            </ul>
            <p className="text-sm text-gray-600 mt-2">
              You can manually trigger any pipeline below if needed, but be aware of the execution time.
            </p>
          </div>
        }
      />

      {/* Pipeline Control Buttons */}
      <div className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Daily Pipeline */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Daily Data Pipeline</h3>
          </div>

          <div className="mb-4">
            <p className="text-sm text-gray-600">Duration: ~5 minutes</p>
            <p className="text-sm text-gray-600">Schedule: Daily (automated)</p>
          </div>

          <button
            onClick={() => runPipeline('daily')}
            disabled={runningPipelines.has('daily')}
            title="Execute the daily data pipeline now. This will refresh all materialized views and update market data. Safe to run anytime."
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {runningPipelines.has('daily') ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Now
              </>
            )}
          </button>
        </div>

        {/* Weekly ML Training */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Weekly ML Training</h3>
          </div>

          <div className="mb-4">
            <p className="text-sm text-gray-600">Duration: ~30-60 minutes</p>
            <p className="text-sm text-gray-600">Schedule: Weekly (Sundays)</p>
          </div>

          <button
            onClick={() => runPipeline('weekly-ml')}
            disabled={runningPipelines.has('weekly_ml')}
            title="Train all 12 XGBoost models for stock screening. This updates the ML models used for portfolio generation. May take 30-60 minutes."
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {runningPipelines.has('weekly_ml') ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Now
              </>
            )}
          </button>
        </div>

        {/* Monthly RL Training */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Monthly RL Training</h3>
          </div>

          <div className="mb-4">
            <p className="text-sm text-gray-600">Duration: ~2-4 hours</p>
            <p className="text-sm text-gray-600">Schedule: Monthly (1st)</p>
          </div>

          <button
            onClick={() => runPipeline('monthly-rl')}
            disabled={runningPipelines.has('monthly_rl')}
            title="Train all 12 PPO reinforcement learning agents for portfolio optimization. Requires GPU for best performance. May take 2-4 hours."
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {runningPipelines.has('monthly_rl') ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Now
              </>
            )}
          </button>
        </div>
      </div>

      {/* Pipeline Job History */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Recent Pipeline Jobs</h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Job ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Pipeline Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Started
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                    No pipeline jobs yet. Run a pipeline to get started.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.job_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {job.job_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {job.pipeline_type === 'daily' && 'Daily Data'}
                      {job.pipeline_type === 'weekly_ml' && 'Weekly ML Training'}
                      {job.pipeline_type === 'monthly_rl' && 'Monthly RL Training'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${job.status === 'completed' ? 'bg-green-100 text-green-800' : ''}
                        ${job.status === 'running' ? 'bg-blue-100 text-blue-800' : ''}
                        ${job.status === 'failed' ? 'bg-red-100 text-red-800' : ''}
                        ${job.status === 'pending' ? 'bg-gray-100 text-gray-800' : ''}
                      `}>
                        {job.status === 'completed' && <CheckCircle className="w-3 h-3" />}
                        {job.status === 'running' && <Clock className="w-3 h-3 animate-spin" />}
                        {job.status === 'failed' && <XCircle className="w-3 h-3" />}
                        {job.status === 'pending' && <AlertCircle className="w-3 h-3" />}
                        {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {job.started_at ? new Date(job.started_at).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDuration(job.started_at, job.completed_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
