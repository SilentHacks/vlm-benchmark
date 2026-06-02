import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ModelStats, SelectivePoint } from '../api'

interface ReliabilityPanelProps {
  byModel: Record<string, ModelStats>
}

const MODEL_COLORS = ['#38bdf8', '#a78bfa', '#4ade80', '#fbbf24', '#f87171']

export default function ReliabilityPanel({ byModel }: ReliabilityPanelProps) {
  const models = Object.entries(byModel).filter(
    ([, s]) => s.reliability?.confidence_available && (s.reliability?.bins?.length ?? 0) > 0,
  )
  if (models.length === 0) {
    const note = Object.values(byModel)[0]?.reliability?.note
    return (
      <div className="card">
        <h2>Reliability &amp; efficiency</h2>
        <p className="muted">
          {note ||
            'No confidence data in this run. Add metric.confidence to your benchmark config and ensure models return a confidence field.'}
        </p>
      </div>
    )
  }

  const calibrationData = buildCalibrationChartData(models)
  const selectiveModel = models[0]
  const selective = selectiveModel[1].reliability?.selective ?? []

  return (
    <>
      <div className="card">
        <h2>Efficiency</h2>
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>$/correct</th>
              <th>$/inference</th>
              <th>Score/USD</th>
              <th>Throughput (P50)</th>
              <th>ECE</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(byModel).map(([model, stats]) => {
              const eff = stats.efficiency
              const rel = stats.reliability
              return (
                <tr key={model}>
                  <td>{model}</td>
                  <td>{formatUsd(eff?.cost_per_correct_usd)}</td>
                  <td>{formatUsd(eff?.cost_per_inference_usd)}</td>
                  <td>{eff?.score_per_usd != null ? eff.score_per_usd.toFixed(1) : '—'}</td>
                  <td>
                    {eff?.throughput_p50_ips != null
                      ? `${eff.throughput_p50_ips.toFixed(2)} img/s`
                      : '—'}
                  </td>
                  <td>{rel?.ece != null ? rel.ece.toFixed(4) : '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="card chart-container">
        <h2>Calibration (confidence vs accuracy)</h2>
        <p className="muted chart-hint">
          Points on the diagonal are well calibrated. Distance above the line suggests overconfidence.
        </p>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={calibrationData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis
              type="number"
              dataKey="mean_confidence"
              domain={[0, 1]}
              stroke="#94a3b8"
              label={{ value: 'Mean confidence', position: 'insideBottom', offset: -4, fill: '#94a3b8' }}
            />
            <YAxis
              type="number"
              domain={[0, 1]}
              stroke="#94a3b8"
              label={{ value: 'Accuracy', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
            />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#64748b" strokeDasharray="4 4" />
            {models.map(([modelId], i) => (
              <Line
                key={modelId}
                type="monotone"
                dataKey={`accuracy_${i}`}
                name={modelId.split(':').pop() || modelId}
                stroke={MODEL_COLORS[i % MODEL_COLORS.length]}
                dot={{ r: 4 }}
                connectNulls
              />
            ))}
            <Legend />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {selective.length > 0 && (
        <div className="card chart-container">
          <h2>Selective prediction ({selectiveModel[0]})</h2>
          <p className="muted chart-hint">
            Accuracy when only approving predictions at or above each confidence threshold.
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={selectiveToChart(selective)} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="threshold" stroke="#94a3b8" />
              <YAxis domain={[0, 1]} stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155' }} />
              <Line type="monotone" dataKey="accuracy" stroke="#38bdf8" name="Accuracy" dot />
              <Line type="monotone" dataKey="coverage" stroke="#a78bfa" name="Coverage" dot />
              <Legend />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </>
  )
}

function buildCalibrationChartData(
  models: [string, ModelStats][],
): Array<Record<string, number | null>> {
  const allBins = new Set<number>()
  for (const [, stats] of models) {
    for (const b of stats.reliability?.bins ?? []) {
      allBins.add(b.mean_confidence)
    }
  }
  const sorted = Array.from(allBins).sort((a, b) => a - b)
  return sorted.map((meanConf) => {
    const row: Record<string, number | null> = { mean_confidence: meanConf }
    models.forEach(([, stats], i) => {
      const bin = (stats.reliability?.bins ?? []).find(
        (b) => Math.abs(b.mean_confidence - meanConf) < 0.0001,
      )
      row[`accuracy_${i}`] = bin?.accuracy ?? null
    })
    return row
  })
}

function selectiveToChart(points: SelectivePoint[]) {
  return points
    .filter((p) => p.accuracy != null)
    .map((p) => ({
      threshold: p.threshold,
      accuracy: p.accuracy,
      coverage: p.coverage,
    }))
}

function formatUsd(value: number | null | undefined): string {
  if (value == null) return '—'
  return `$${value.toFixed(4)}`
}
