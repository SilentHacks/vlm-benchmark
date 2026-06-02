import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import CostAccuracyChart, { modelStatsToSeries } from '../components/CostAccuracyChart'
import FrontierChart, { modelStatsToLatencySeries } from '../components/FrontierChart'
import ReliabilityPanel from '../components/ReliabilityPanel'
import { fetchRunResults, MetricRow, ModelStats, thumbnailUrl } from '../api'

export default function Results() {
  const { id } = useParams<{ id: string }>()
  const [byModel, setByModel] = useState<Record<string, ModelStats>>({})
  const [metrics, setMetrics] = useState<MetricRow[]>([])
  const [filter, setFilter] = useState<'all' | 'failures' | 'disagreements'>('all')
  const [error, setError] = useState('')
  const [modal, setModal] = useState<{ imageId: string; rows: MetricRow[] } | null>(null)

  useEffect(() => {
    if (!id) return
    fetchRunResults(id)
      .then((data) => {
        setByModel(data.aggregates.by_model || {})
        setMetrics(data.metrics)
      })
      .catch((e) => setError(e.message))
  }, [id])

  if (error) return <p className="error">{error}</p>

  const sortedModels = Object.entries(byModel).sort((a, b) => b[1].primary_score - a[1].primary_score)
  const filtered = filterMetrics(metrics, filter)
  const chartData = sortedModels.map(([model, stats]) => ({
    model: model.split(':').pop() || model,
    score: stats.primary_score,
  }))

  return (
    <div>
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ marginBottom: 0 }}>Results</h2>
        {id && (
          <Link to={`/compare?baseline=${id}`} className="btn btn-secondary">
            Compare with...
          </Link>
        )}
      </div>

      <div className="card">
        <h2>Leaderboard</h2>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Model</th>
              <th>Score</th>
              <th>Correct/Total</th>
              <th>P50 Latency</th>
              <th>Cost USD</th>
              <th>$/correct</th>
              <th>ECE</th>
              <th>Errors</th>
            </tr>
          </thead>
          <tbody>
            {sortedModels.map(([model, stats], i) => (
              <tr key={model}>
                <td>{i + 1}</td>
                <td>{model}</td>
                <td className={i === 0 ? 'best' : ''}>{stats.primary_score.toFixed(3)}</td>
                <td>{stats.correct}/{stats.total}</td>
                <td>{stats.latency_ms?.p50?.toFixed(0) ?? '—'} ms</td>
                <td>${stats.cost_usd?.toFixed(4) ?? '0.0000'}</td>
                <td>{formatUsd(stats.efficiency?.cost_per_correct_usd)}</td>
                <td>{stats.reliability?.ece != null ? stats.reliability.ece.toFixed(4) : '—'}</td>
                <td>{stats.errors ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {chartData.length > 0 && (
        <div className="card chart-container">
          <h2>Score by Model</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="model" stroke="#94a3b8" />
              <YAxis domain={[0, 1]} stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
              <Bar dataKey="score" fill="#38bdf8" name="Primary Score" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <CostAccuracyChart
        title="Cost vs Accuracy"
        series={[modelStatsToSeries(byModel, 'Models', '#38bdf8')]}
      />

      <FrontierChart
        title="Latency (P50) vs Accuracy"
        xLabel="P50 latency (ms)"
        xTickFormat={(v) => `${v.toFixed(0)} ms`}
        series={[modelStatsToLatencySeries(byModel, 'Models', '#a78bfa')]}
      />

      <ReliabilityPanel byModel={byModel} />

      <div className="card">
        <h2>Per-Image Comparison</h2>
        <div style={{ marginBottom: '1rem' }}>
          <select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)}>
            <option value="all">All</option>
            <option value="failures">Failures only</option>
            <option value="disagreements">Disagreements only</option>
          </select>
        </div>
        <div className="grid-images">
          {groupByImage(filtered).map(([imageId, rows]) => (
            <div
              key={imageId}
              className="grid-item"
              onClick={() => setModal({ imageId, rows })}
              role="button"
              tabIndex={0}
            >
              <img src={thumbnailUrl(rows[0].image_path || `fixtures/images/${imageId}.png`)} alt={imageId} />
              <strong>{imageId}</strong>
              {rows.map((r) => (
                <div key={r.model_id} className="model-row">
                  <span>{r.model_id.split(':').pop()}: </span>
                  <span className={r.passed ? 'pass' : 'fail'}>
                    {r.passed ? 'PASS' : 'FAIL'} {r.score.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{modal.imageId}</h2>
            <img src={thumbnailUrl(modal.rows[0]?.image_path || `fixtures/images/${modal.imageId}.png`)} alt={modal.imageId} className="modal-img" />
            {modal.rows.map((r) => (
              <div key={r.model_id} className="modal-model">
                <strong>{r.model_id}</strong>
                <span className={r.passed ? 'pass' : 'fail'}>
                  {r.passed ? 'PASS' : 'FAIL'} — {r.score.toFixed(2)}
                </span>
              </div>
            ))}
            <button type="button" className="btn" onClick={() => setModal(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  )
}

function formatUsd(value: number | null | undefined): string {
  if (value == null) return '—'
  return `$${value.toFixed(4)}`
}

function groupByImage(metrics: MetricRow[]): [string, MetricRow[]][] {
  const map = new Map<string, MetricRow[]>()
  for (const m of metrics) {
    if (!map.has(m.image_id)) map.set(m.image_id, [])
    map.get(m.image_id)!.push(m)
  }
  return Array.from(map.entries())
}

function filterMetrics(metrics: MetricRow[], filter: string): MetricRow[] {
  if (filter === 'failures') return metrics.filter((m) => !m.passed)
  if (filter === 'disagreements') {
    const byImage = groupByImage(metrics)
    const disagreeImages = new Set(
      byImage.filter(([, rows]) => {
        const passes = rows.map((r) => r.passed)
        return passes.some(Boolean) && passes.some((p) => !p)
      }).map(([id]) => id),
    )
    return metrics.filter((m) => disagreeImages.has(m.image_id))
  }
  return metrics
}
