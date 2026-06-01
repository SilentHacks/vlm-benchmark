import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchRun, RunDetail } from '../api'

const API = import.meta.env.VITE_API_URL || '/api'

export default function RunView() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [events, setEvents] = useState<string[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    fetchRun(id).then(setRun).catch((e) => setError(e.message))

    const es = new EventSource(`${API}/runs/${id}/events`)
    es.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'progress') {
        setEvents((prev) => [
          ...prev,
          `${data.model_id} × ${data.image_id}: score=${data.score?.toFixed?.(2) ?? '—'}`,
        ])
        setRun((prev) =>
          prev
            ? {
                ...prev,
                progress_completed: data.completed ?? data.progress_completed ?? prev.progress_completed,
                progress_total: data.total ?? data.progress_total ?? prev.progress_total,
              }
            : prev,
        )
      }
      if (data.type === 'complete' || data.type === 'done') {
        fetchRun(id!).then(setRun)
        es.close()
      }
    }
    return () => es.close()
  }, [id])

  if (error) return <p className="error">{error}</p>
  if (!run) return <p>Loading run...</p>

  const total = run.progress_total ?? 0
  const completed = run.progress_completed ?? 0
  const pct = total > 0 ? (completed / total) * 100 : 0

  return (
    <div>
      <div className="card">
        <h2>{run.name}</h2>
        <p>Status: <strong>{run.status}</strong> · ID: {run.id}</p>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <p>{completed} / {total} tasks</p>
        {run.status === 'completed' && (
          <Link to={`/runs/${run.id}/results`} className="btn">View Results</Link>
        )}
      </div>
      {events.length > 0 && (
        <div className="card">
          <h2>Live Progress</h2>
          <div className="event-log">
            {events.map((ev, i) => <div key={i}>{ev}</div>)}
          </div>
        </div>
      )}
    </div>
  )
}
