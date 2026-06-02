import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import CostAccuracyChart, { modelStatsToSeries } from '../components/CostAccuracyChart'
import {
  CompareResult,
  CompareRow,
  fetchCompareRuns,
  fetchRuns,
  Run,
  thumbnailUrl,
} from '../api'

type RowFilter = 'all' | 'regressions' | 'improvements' | 'unchanged'

export default function Compare() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [runs, setRuns] = useState<Run[]>([])
  const [baselineId, setBaselineId] = useState(searchParams.get('baseline') || '')
  const [candidateId, setCandidateId] = useState(searchParams.get('candidate') || '')
  const [result, setResult] = useState<CompareResult | null>(null)
  const [filter, setFilter] = useState<RowFilter>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [modal, setModal] = useState<CompareRow | null>(null)

  useEffect(() => {
    fetchRuns()
      .then((all) => setRuns(all.filter((r) => r.status === 'completed')))
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!baselineId || !candidateId) {
      setResult(null)
      return
    }
    setLoading(true)
    setError('')
    fetchCompareRuns(baselineId, candidateId)
      .then((data) => {
        setResult(data)
        setSearchParams({ baseline: baselineId, candidate: candidateId })
      })
      .catch((e) => {
        setResult(null)
        setError(e.message)
      })
      .finally(() => setLoading(false))
  }, [baselineId, candidateId, setSearchParams])

  const completedRuns = runs

  const filteredRows = result
    ? filterCompareRows(result.rows, filter)
    : []

  const paretoSeries = result
    ? [
        modelStatsToSeries(
          Object.fromEntries(
            result.summary_by_model.map((s) => [
              s.model_id,
              { primary_score: s.baseline_score, cost_usd: s.baseline_cost },
            ]),
          ),
          'Baseline',
          '#64748b',
        ),
        modelStatsToSeries(
          Object.fromEntries(
            result.summary_by_model.map((s) => [
              s.model_id,
              { primary_score: s.candidate_score, cost_usd: s.candidate_cost },
            ]),
          ),
          'Candidate',
          '#38bdf8',
        ),
      ]
    : []

  return (
    <div>
      <div className="card">
        <h2>Compare Runs</h2>
        <div className="compare-selectors">
          <div className="form-group">
            <label htmlFor="baseline">Baseline run</label>
            <select
              id="baseline"
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value)}
            >
              <option value="">Select baseline...</option>
              {completedRuns.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.id}) — {new Date(r.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="candidate">Candidate run</label>
            <select
              id="candidate"
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
            >
              <option value="">Select candidate...</option>
              {completedRuns.map((r) => (
                <option key={r.id} value={r.id} disabled={r.id === baselineId}>
                  {r.name} ({r.id}) — {new Date(r.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>
        </div>
        {loading && <p>Loading comparison...</p>}
        {error && <p className="error">{error}</p>}
        {result && result.warnings.length > 0 && (
          <div className="error">
            {result.warnings.map((w) => (
              <p key={w}>{w}</p>
            ))}
          </div>
        )}
      </div>

      {result && (
        <>
          <div className="card">
            <h2>Summary</h2>
            <p>
              {result.counts.improved} improved · {result.counts.regressed} regressed ·{' '}
              {result.counts.unchanged} unchanged
            </p>
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Baseline Score</th>
                  <th>Candidate Score</th>
                  <th>Delta</th>
                  <th>Baseline Cost</th>
                  <th>Candidate Cost</th>
                  <th>Cost Δ</th>
                  <th>↑</th>
                  <th>↓</th>
                </tr>
              </thead>
              <tbody>
                {result.summary_by_model.map((row) => (
                  <tr key={row.model_id}>
                    <td>{row.model_id}</td>
                    <td>{row.baseline_score.toFixed(3)}</td>
                    <td>{row.candidate_score.toFixed(3)}</td>
                    <td className={row.score_delta > 0 ? 'delta-pos' : row.score_delta < 0 ? 'delta-neg' : ''}>
                      {row.score_delta >= 0 ? '+' : ''}{row.score_delta.toFixed(3)}
                    </td>
                    <td>${row.baseline_cost.toFixed(4)}</td>
                    <td>${row.candidate_cost.toFixed(4)}</td>
                    <td className={row.cost_delta < 0 ? 'delta-pos' : row.cost_delta > 0 ? 'delta-neg' : ''}>
                      {row.cost_delta >= 0 ? '+' : ''}${row.cost_delta.toFixed(4)}
                    </td>
                    <td>{row.improvements}</td>
                    <td>{row.regressions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <CostAccuracyChart title="Cost vs Accuracy (Both Runs)" series={paretoSeries} />

          <div className="card">
            <h2>Per-Image Changes</h2>
            <div style={{ marginBottom: '1rem' }}>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as RowFilter)}
              >
                <option value="all">All</option>
                <option value="regressions">Regressions only</option>
                <option value="improvements">Improvements only</option>
                <option value="unchanged">Unchanged only</option>
              </select>
            </div>
            <div className="grid-images">
              {groupCompareByImage(filteredRows).map(([imageId, rows]) => (
                <div
                  key={imageId}
                  className="grid-item"
                  onClick={() => setModal(rows[0])}
                  role="button"
                  tabIndex={0}
                >
                  <img
                    src={thumbnailUrl(rows[0].image_path || `fixtures/images/${imageId}.png`)}
                    alt={imageId}
                  />
                  <strong>{imageId}</strong>
                  {rows.map((r) => (
                    <div key={r.model_id} className="model-row">
                      <span>{r.model_id.split(':').pop()}: </span>
                      <span className={changeClass(r.change)}>
                        {r.change.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            {filteredRows.length === 0 && <p>No rows match this filter.</p>}
          </div>
        </>
      )}

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{modal.image_id}</h2>
            <p><strong>{modal.model_id}</strong></p>
            <img
              src={thumbnailUrl(modal.image_path || `fixtures/images/${modal.image_id}.png`)}
              alt={modal.image_id}
              className="modal-img"
            />
            <div className="modal-model">
              <span>Baseline</span>
              <span className={modal.baseline?.passed ? 'pass' : 'fail'}>
                {modal.baseline
                  ? `${modal.baseline.passed ? 'PASS' : 'FAIL'} — ${modal.baseline.score.toFixed(2)}`
                  : '—'}
              </span>
            </div>
            <div className="modal-model">
              <span>Candidate</span>
              <span className={modal.candidate?.passed ? 'pass' : 'fail'}>
                {modal.candidate
                  ? `${modal.candidate.passed ? 'PASS' : 'FAIL'} — ${modal.candidate.score.toFixed(2)}`
                  : '—'}
              </span>
            </div>
            <p>Change: <span className={changeClass(modal.change)}>{modal.change.replace('_', ' ')}</span></p>
            <button type="button" className="btn" onClick={() => setModal(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  )
}

function filterCompareRows(rows: CompareRow[], filter: RowFilter): CompareRow[] {
  if (filter === 'regressions') return rows.filter((r) => r.change === 'regressed')
  if (filter === 'improvements') return rows.filter((r) => r.change === 'improved')
  if (filter === 'unchanged') return rows.filter((r) => r.change === 'unchanged')
  return rows
}

function groupCompareByImage(rows: CompareRow[]): [string, CompareRow[]][] {
  const map = new Map<string, CompareRow[]>()
  for (const r of rows) {
    if (!map.has(r.image_id)) map.set(r.image_id, [])
    map.get(r.image_id)!.push(r)
  }
  return Array.from(map.entries())
}

function changeClass(change: CompareRow['change']): string {
  if (change === 'improved') return 'pass'
  if (change === 'regressed') return 'fail'
  return ''
}
