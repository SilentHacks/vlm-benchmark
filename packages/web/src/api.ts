const API = import.meta.env.VITE_API_URL || '/api'

export interface Run {
  id: string
  name: string
  status: string
  progress_completed: number
  progress_total: number
  created_at: string
  finished_at?: string
}

export interface RunDetail extends Run {
  aggregates: { by_model?: Record<string, ModelStats> }
}

export interface CalibrationBin {
  bin_low: number
  bin_high: number
  count: number
  mean_confidence: number
  accuracy: number
  gap: number
}

export interface SelectivePoint {
  threshold: number
  coverage: number
  accuracy: number | null
  mean_cost_usd: number | null
  mean_latency_ms: number | null
  approved_count: number
}

export interface ReliabilityStats {
  sample_count: number
  confidence_count: number
  confidence_available: boolean
  ece: number | null
  mce: number | null
  bins: CalibrationBin[]
  selective: SelectivePoint[]
  note: string | null
}

export interface EfficiencyStats {
  cost_per_correct_usd: number | null
  cost_per_inference_usd: number | null
  score_per_usd: number | null
  throughput_p50_ips: number | null
  latency_ms_per_correct_p50: number | null
}

export interface ModelStats {
  primary_score: number
  correct: number
  total: number
  latency_ms: { p50: number; p95: number; mean: number }
  cost_usd: number
  errors: number
  reliability?: ReliabilityStats
  efficiency?: EfficiencyStats
}

export interface MetricRow {
  image_id: string
  model_id: string
  score: number
  passed: boolean
  image_path?: string
  details: Record<string, unknown>
}

export interface CompareSide {
  score: number
  passed: boolean
}

export interface CompareRow {
  image_id: string
  model_id: string
  image_path: string
  baseline: CompareSide | null
  candidate: CompareSide | null
  change: 'improved' | 'regressed' | 'unchanged' | 'baseline_only' | 'candidate_only'
}

export interface CompareModelSummary {
  model_id: string
  baseline_score: number
  candidate_score: number
  score_delta: number
  baseline_cost: number
  candidate_cost: number
  cost_delta: number
  baseline_errors: number
  candidate_errors: number
  improvements: number
  regressions: number
  unchanged: number
}

export interface CompareResult {
  baseline: { run_id: string; name: string; status: string; created_at: string | null; finished_at: string | null }
  candidate: { run_id: string; name: string; status: string; created_at: string | null; finished_at: string | null }
  warnings: string[]
  summary_by_model: CompareModelSummary[]
  rows: CompareRow[]
  counts: {
    improved: number
    regressed: number
    unchanged: number
    baseline_only: number
    candidate_only: number
  }
}

export async function fetchRuns(): Promise<Run[]> {
  const res = await fetch(`${API}/runs`)
  if (!res.ok) throw new Error('Failed to fetch runs')
  return res.json()
}

export async function fetchRun(id: string): Promise<RunDetail> {
  const res = await fetch(`${API}/runs/${id}`)
  if (!res.ok) throw new Error('Failed to fetch run')
  return res.json()
}

export async function fetchRunResults(id: string): Promise<{
  metrics: MetricRow[]
  aggregates: { by_model?: Record<string, ModelStats> }
}> {
  const res = await fetch(`${API}/runs/${id}/results`)
  if (!res.ok) throw new Error('Failed to fetch results')
  return res.json()
}

export async function createRun(configYaml: string): Promise<{ id: string }> {
  const res = await fetch(`${API}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config_yaml: configYaml }),
  })
  if (!res.ok) throw new Error('Failed to create run')
  const data = await res.json()
  return { id: data.id || data.run_id }
}

export async function validateConfig(config: Record<string, unknown>): Promise<{ valid: boolean; errors: string[] }> {
  const res = await fetch(`${API}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error('Validation failed')
  return res.json()
}

export function thumbnailUrl(imagePath: string): string {
  return `${API}/thumbnails/${encodeURIComponent(imagePath)}`
}

export async function fetchCompareRuns(
  baseline: string,
  candidate: string,
  strictName = true,
): Promise<CompareResult> {
  const params = new URLSearchParams({
    baseline,
    candidate,
    strict_name: String(strictName),
  })
  const res = await fetch(`${API}/runs/compare?${params}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || 'Failed to compare runs')
  }
  return res.json()
}
