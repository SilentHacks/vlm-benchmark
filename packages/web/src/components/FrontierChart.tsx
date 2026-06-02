import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

export interface FrontierPoint {
  model: string
  fullModel: string
  x: number
  score: number
}

export interface FrontierSeries {
  name: string
  color: string
  points: FrontierPoint[]
}

interface FrontierChartProps {
  series: FrontierSeries[]
  title: string
  xLabel: string
  xTickFormat?: (v: number) => string
}

function FrontierTooltip({
  active,
  payload,
  xLabel,
}: {
  active?: boolean
  payload?: Array<{ payload: FrontierPoint & { seriesName?: string } }>
  xLabel: string
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div
      style={{
        background: '#1e293b',
        border: '1px solid #334155',
        borderRadius: 8,
        padding: '0.5rem 0.75rem',
        fontSize: '0.875rem',
      }}
    >
      <div><strong>{p.fullModel}</strong></div>
      {p.seriesName && <div>{p.seriesName}</div>}
      <div>Score: {p.score.toFixed(3)}</div>
      <div>{xLabel}: {p.x.toFixed(4)}</div>
    </div>
  )
}

export default function FrontierChart({
  series,
  title,
  xLabel,
  xTickFormat,
}: FrontierChartProps) {
  const hasData = series.some((s) => s.points.length > 0)
  if (!hasData) return null

  const chartSeries = series.filter((s) => s.points.length > 0)
  const formatX = xTickFormat ?? ((v: number) => String(v))

  return (
    <div className="card chart-container">
      {title && <h2>{title}</h2>}
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number"
            dataKey="x"
            name={xLabel}
            stroke="#94a3b8"
            tickFormatter={formatX}
          />
          <YAxis
            type="number"
            dataKey="score"
            name="Score"
            domain={[0, 1]}
            stroke="#94a3b8"
          />
          <Tooltip content={<FrontierTooltip xLabel={xLabel} />} />
          {chartSeries.length > 1 && <Legend />}
          {chartSeries.map((s) => (
            <Scatter
              key={s.name}
              name={s.name}
              data={s.points.map((p) => ({ ...p, seriesName: s.name }))}
              fill={s.color}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

export function modelStatsToLatencySeries(
  byModel: Record<string, { primary_score: number; latency_ms?: { p50: number } }>,
  name: string,
  color: string,
): FrontierSeries {
  return {
    name,
    color,
    points: Object.entries(byModel)
      .filter(([, stats]) => stats.latency_ms?.p50 != null && stats.latency_ms.p50 > 0)
      .map(([model, stats]) => ({
        model: model.split(':').pop() || model,
        fullModel: model,
        x: stats.latency_ms!.p50,
        score: stats.primary_score ?? 0,
      })),
  }
}
