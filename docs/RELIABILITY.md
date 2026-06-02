# Reliability & efficiency

VLM Benchmark can analyze **model-reported confidence** alongside **cost and latency** so you can pick models for production, not only compare raw accuracy.

## Enabling confidence

Add a `confidence` block under `metric` in your benchmark YAML (alongside `parse` for the label):

```yaml
metric:
  type: classification
  parse:
    mode: json
    path: "$.label"
  confidence:
    path: "$.confidence"
    scale: unit   # unit (0–1) or percent (0–100)
  labels_field: expected_class
  aggregate: accuracy
```

The model response must include a numeric confidence field, for example:

```json
{"label": "defect", "confidence": 0.92}
```

The mock adapter (`mock:deterministic`) always returns `"confidence": 0.95`, so the example config works without API keys.

If `confidence` is omitted from config, runs still complete; reliability sections show a short note instead of charts.

## What gets computed

After each run, aggregates for every model include:

### Reliability (`aggregates.by_model.<model>.reliability`)

| Field | Description |
|-------|-------------|
| `ece` | Expected calibration error — weighted mean of \|mean confidence − accuracy\| per bin |
| `mce` | Maximum calibration gap across bins |
| `bins` | Per-bin count, mean confidence, accuracy, and gap |
| `selective` | At each threshold τ, coverage (% approved), accuracy among approved, mean cost/latency |

ECE requires at least two samples with confidence. Small datasets (e.g. fixtures) are useful for development but interpret ECE cautiously.

### Efficiency (`aggregates.by_model.<model>.efficiency`)

| Field | Description |
|-------|-------------|
| `cost_per_correct_usd` | Total run cost ÷ number of correct predictions |
| `cost_per_inference_usd` | Total cost ÷ number of inferences |
| `score_per_usd` | Primary metric score ÷ total cost (omitted when cost is 0) |
| `throughput_p50_ips` | 1000 / P50 latency (images per second proxy) |

## Where to view results

- **CLI:** `vlm-bench results <RUN_ID>` — ECE and $/correct columns
- **API:** Same fields under `aggregates.by_model` in `GET /runs/{id}/results`
- **Dashboard:** Results page — efficiency table, calibration chart, selective prediction, latency vs accuracy scatter
- **Export:** `vlm-bench export <RUN_ID> --out report.html` includes the extra leaderboard columns

## Interpreting calibration

- **On the diagonal:** mean confidence in a bin matches accuracy (well calibrated).
- **Above the diagonal:** overconfident (reports high confidence but fails more often).
- **Selective prediction:** use when auto-approving only high-confidence outputs — trade coverage for accuracy.

## Future extensions

Provider logprobs, verbalized confidence parsing, and multi-sample agreement confidence are natural follow-ups; the aggregate shape is designed to accept richer per-row confidence without breaking existing clients.
