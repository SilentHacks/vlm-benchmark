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

export interface CostAccuracyPoint {
  model: string
  fullModel: string
  cost: number
  score: number
}

export interface CostAccuracySeries {
  name: string
  color: string
  points: CostAccuracyPoint[]
}

interface CostAccuracyChartProps {
  series: CostAccuracySeries[]
  title?: string
}

function ParetoTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload: CostAccuracyPoint & { seriesName?: string } }>
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
      <div>Cost: ${p.cost.toFixed(4)}</div>
    </div>
  )
}

export default function CostAccuracyChart({ series, title }: CostAccuracyChartProps) {
  const hasData = series.some((s) => s.points.length > 0)
  if (!hasData) return null

  const chartSeries = series.filter((s) => s.points.length > 0)

  return (
    <div className="card chart-container">
      {title && <h2>{title}</h2>}
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            type="number"
            dataKey="cost"
            name="Cost"
            unit=" USD"
            stroke="#94a3b8"
            tickFormatter={(v) => `$${Number(v).toFixed(3)}`}
          />
          <YAxis
            type="number"
            dataKey="score"
            name="Score"
            domain={[0, 1]}
            stroke="#94a3b8"
          />
          <Tooltip content={<ParetoTooltip />} />
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

export function modelStatsToSeries(
  byModel: Record<string, { primary_score: number; cost_usd: number }>,
  name: string,
  color: string,
): CostAccuracySeries {
  return {
    name,
    color,
    points: Object.entries(byModel).map(([model, stats]) => ({
      model: model.split(':').pop() || model,
      fullModel: model,
      cost: stats.cost_usd ?? 0,
      score: stats.primary_score ?? 0,
    })),
  }
}
