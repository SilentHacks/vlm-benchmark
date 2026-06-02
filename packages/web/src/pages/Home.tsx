import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchRuns, Run } from '../api'

export default function Home() {
  const [runs, setRuns] = useState<Run[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchRuns()
      .then(setRuns)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="card">
        <h2>Recent Runs</h2>
        {loading && <p>Loading...</p>}
        {error && <p className="error">{error}</p>}
        {!loading && runs.length === 0 && (
          <p>No runs yet. <Link to="/wizard">Start a benchmark</Link></p>
        )}
        {runs.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{run.name}</td>
                  <td>{run.status}</td>
                  <td>{run.progress_completed}/{run.progress_total}</td>
                  <td>{new Date(run.created_at).toLocaleString()}</td>
                  <td>
                    <Link to={`/runs/${run.id}`}>View</Link>
                    {run.status === 'completed' && (
                      <> · <Link to={`/runs/${run.id}/results`}>Results</Link></>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="card">
        <h2>Quick Start</h2>
        <p>Compare vision-language models on your image datasets with pluggable metrics.</p>
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
          <Link to="/wizard" className="btn">New Benchmark</Link>
          <Link to="/compare" className="btn btn-secondary">Compare Runs</Link>
        </div>
      </div>
    </div>
  )
}
