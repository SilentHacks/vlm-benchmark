import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import YAML from 'js-yaml'
import { createRun, validateConfig } from '../api'

const STEPS = ['Dataset', 'Prompts', 'Models', 'Metric', 'Review']

const DEFAULT_CONFIG = {
  name: 'my-benchmark',
  prompts: {
    system: 'You are a visual inspector.',
    user: 'Classify this image. Reply JSON only: {"label": "<class>"}',
  },
  dataset: {
    manifest: 'fixtures/manifest.jsonl',
    base_dir: 'fixtures',
  },
  models: ['mock:deterministic'],
  metric: {
    type: 'classification',
    parse: { mode: 'json', path: '$.label' },
    confidence: { path: '$.confidence', scale: 'unit' },
    labels_field: 'expected_class',
    aggregate: 'accuracy',
  },
  execution: { max_concurrency: 4, cache: true },
}

export default function Wizard() {
  const [step, setStep] = useState(0)
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [errors, setErrors] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const navigate = useNavigate()

  const update = (path: string, value: unknown) => {
    setConfig((prev) => {
      const next = structuredClone(prev)
      const keys = path.split('.')
      let obj: Record<string, unknown> = next
      for (let i = 0; i < keys.length - 1; i++) {
        obj = obj[keys[i]] as Record<string, unknown>
      }
      obj[keys[keys.length - 1]] = value
      return next
    })
  }

  const handleValidate = async () => {
    try {
      const result = await validateConfig(config)
      setErrors(result.errors)
      return result.valid
    } catch {
      setErrors(['API unavailable — config saved locally'])
      return true
    }
  }

  const handleRun = async () => {
    setRunning(true)
    const valid = await handleValidate()
    if (!valid) { setRunning(false); return }
    try {
      const yaml = configToYaml(config)
      const { id } = await createRun(yaml)
      navigate(`/runs/${id}`)
    } catch (e) {
      setErrors([(e as Error).message])
      setRunning(false)
    }
  }

  return (
    <div>
      <div className="wizard-steps">
        {STEPS.map((s, i) => (
          <div key={s} className={`step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
            {i + 1}. {s}
          </div>
        ))}
      </div>

      <div className="card">
        {step === 0 && (
          <>
            <h2>Dataset</h2>
            <div className="form-group">
              <label>Benchmark Name</label>
              <input value={config.name} onChange={(e) => update('name', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Manifest Path</label>
              <input value={config.dataset.manifest} onChange={(e) => update('dataset.manifest', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Base Directory</label>
              <input value={config.dataset.base_dir} onChange={(e) => update('dataset.base_dir', e.target.value)} />
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h2>Prompts</h2>
            <div className="form-group">
              <label>System Prompt</label>
              <textarea rows={3} value={config.prompts.system} onChange={(e) => update('prompts.system', e.target.value)} />
            </div>
            <div className="form-group">
              <label>User Prompt</label>
              <textarea rows={3} value={config.prompts.user} onChange={(e) => update('prompts.user', e.target.value)} />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h2>Models</h2>
            <div className="form-group">
              <label>Models (comma-separated)</label>
              <input
                value={config.models.join(', ')}
                onChange={(e) => update('models', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
              />
            </div>
            <p style={{ fontSize: '0.875rem', color: '#64748b' }}>
              Available: mock:deterministic, openai:gpt-4o, google:gemini-2.0-flash, anthropic:claude-3-5-sonnet-20241022
            </p>
          </>
        )}

        {step === 3 && (
          <>
            <h2>Metric</h2>
            <div className="form-group">
              <label>Metric Type</label>
              <select value={config.metric.type} onChange={(e) => update('metric.type', e.target.value)}>
                <option value="classification">classification</option>
                <option value="exact_match">exact_match</option>
                <option value="json_field_match">json_field_match</option>
                <option value="contains_keywords">contains_keywords</option>
                <option value="regex">regex</option>
                <option value="json_schema">json_schema</option>
              </select>
            </div>
            <div className="form-group">
              <label>Labels Field (manifest column)</label>
              <input value={config.metric.labels_field || ''} onChange={(e) => update('metric.labels_field', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Aggregate</label>
              <select value={config.metric.aggregate} onChange={(e) => update('metric.aggregate', e.target.value)}>
                <option value="accuracy">accuracy</option>
                <option value="macro_f1">macro_f1</option>
              </select>
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <h2>Review & Run</h2>
            <pre style={{ background: '#f1f5f9', padding: '1rem', borderRadius: '8px', fontSize: '0.8rem', overflow: 'auto' }}>
              {configToYaml(config)}
            </pre>
            {errors.length > 0 && errors.map((e) => <p key={e} className="error">{e}</p>)}
          </>
        )}

        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
          {step > 0 && <button className="btn" onClick={() => setStep(step - 1)}>Back</button>}
          {step < STEPS.length - 1 && (
            <button className="btn" onClick={() => setStep(step + 1)}>Next</button>
          )}
          {step === STEPS.length - 1 && (
            <button className="btn" onClick={handleRun} disabled={running}>
              {running ? 'Starting...' : 'Run Benchmark'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function configToYaml(config: typeof DEFAULT_CONFIG): string {
  return YAML.stringify(config)
}
