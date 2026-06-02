"""HTML report export."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, Template

from vlm_bench.compare import compare_runs
from vlm_bench.results import load_run_results

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>VLM Benchmark — {{ run_id }}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; background: #0f1117; color: #e4e4e7; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #333; padding: 0.5rem 1rem; text-align: left; }
    th { background: #1e2130; }
    .pass { color: #4ade80; }
    .fail { color: #f87171; }
    h1 { color: #a78bfa; }
  </style>
</head>
<body>
  <h1>Benchmark Report: {{ name }}</h1>
  <p>Run ID: <code>{{ run_id }}</code> | Status: {{ status }}</p>
  <h2>Leaderboard</h2>
  <table>
    <tr><th>Model</th><th>Score</th><th>Correct/Total</th><th>Cost USD</th><th>$/correct</th><th>ECE</th><th>P50 ms</th><th>Errors</th></tr>
    {% for row in leaderboard %}
    <tr>
      <td>{{ row.model_id }}</td>
      <td>{{ "%.4f"|format(row.score) }}</td>
      <td>{{ row.correct }}/{{ row.total }}</td>
      <td>${{ "%.4f"|format(row.cost) }}</td>
      <td>{{ row.cost_per_correct }}</td>
      <td>{{ row.ece }}</td>
      <td>{{ row.p50_ms }}</td>
      <td>{{ row.errors }}</td>
    </tr>
    {% endfor %}
  </table>
  <h2>Per-image results</h2>
  <table>
    <tr><th>Image</th><th>Model</th><th>Score</th><th>Pass</th></tr>
    {% for m in metrics %}
    <tr>
      <td>{{ m.image_id }}</td>
      <td>{{ m.model_id }}</td>
      <td>{{ "%.2f"|format(m.score) }}</td>
      <td class="{{ 'pass' if m.passed else 'fail' }}">{{ '✓' if m.passed else '✗' }}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

COMPARE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>VLM Benchmark Compare — {{ baseline_id }} vs {{ candidate_id }}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; background: #0f1117; color: #e4e4e7; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #333; padding: 0.5rem 1rem; text-align: left; }
    th { background: #1e2130; }
    .pass { color: #4ade80; }
    .fail { color: #f87171; }
    .improved { color: #4ade80; }
    .regressed { color: #f87171; }
    h1 { color: #a78bfa; }
    .warn { color: #fbbf24; }
  </style>
</head>
<body>
  <h1>Run Comparison</h1>
  <p>Baseline: <code>{{ baseline_id }}</code> ({{ baseline_name }})</p>
  <p>Candidate: <code>{{ candidate_id }}</code> ({{ candidate_name }})</p>
  {% for w in warnings %}
  <p class="warn">Warning: {{ w }}</p>
  {% endfor %}

  <h2>Model Summary</h2>
  <table>
    <tr>
      <th>Model</th><th>Baseline Score</th><th>Candidate Score</th><th>Delta</th>
      <th>Baseline Cost</th><th>Candidate Cost</th><th>Cost Delta</th>
      <th>Improved</th><th>Regressed</th>
    </tr>
    {% for row in summary %}
    <tr>
      <td>{{ row.model_id }}</td>
      <td>{{ "%.4f"|format(row.baseline_score) }}</td>
      <td>{{ "%.4f"|format(row.candidate_score) }}</td>
      <td>{{ "%+.4f"|format(row.score_delta) }}</td>
      <td>${{ "%.4f"|format(row.baseline_cost) }}</td>
      <td>${{ "%.4f"|format(row.candidate_cost) }}</td>
      <td>${{ "%+.4f"|format(row.cost_delta) }}</td>
      <td>{{ row.improvements }}</td>
      <td>{{ row.regressions }}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Regressions</h2>
  <table>
    <tr><th>Image</th><th>Model</th><th>Baseline</th><th>Candidate</th></tr>
    {% for row in regressions %}
    <tr>
      <td>{{ row.image_id }}</td>
      <td>{{ row.model_id }}</td>
      <td class="pass">PASS</td>
      <td class="fail">FAIL</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Improvements</h2>
  <table>
    <tr><th>Image</th><th>Model</th><th>Baseline</th><th>Candidate</th></tr>
    {% for row in improvements %}
    <tr>
      <td>{{ row.image_id }}</td>
      <td>{{ row.model_id }}</td>
      <td class="fail">FAIL</td>
      <td class="pass">PASS</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""


def render_html_report(run_id: str, db_path: str | Path) -> str:
    dto = load_run_results(db_path, run_id)
    run = dto.run
    by_model = dto.aggregates.get("by_model", {})
    metrics = dto.metrics

    leaderboard = []
    for model_id, agg in by_model.items():
        eff = agg.get("efficiency") or {}
        rel = agg.get("reliability") or {}
        lat = agg.get("latency_ms") or {}
        cpc = eff.get("cost_per_correct_usd")
        ece = rel.get("ece")
        leaderboard.append(
            {
                "model_id": model_id,
                "score": agg.get("primary_score", 0),
                "correct": agg.get("correct", 0),
                "total": agg.get("total", 0),
                "cost": agg.get("cost_usd", 0),
                "cost_per_correct": f"${cpc:.4f}" if cpc is not None else "—",
                "ece": f"{ece:.4f}" if ece is not None else "—",
                "p50_ms": f"{lat['p50']:.0f}" if lat.get("p50") is not None else "—",
                "errors": agg.get("errors", 0),
            }
        )
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    env = Environment(autoescape=True)
    tmpl = env.from_string(REPORT_TEMPLATE)
    return tmpl.render(
        run_id=run_id,
        name=run.name,
        status=run.status,
        leaderboard=leaderboard,
        metrics=[
            {
                "image_id": m.image_id,
                "model_id": m.model_id,
                "score": m.score,
                "passed": m.passed,
            }
            for m in metrics
        ],
    )


def render_compare_html_report(
    baseline_id: str,
    candidate_id: str,
    db_path: str | Path,
    *,
    strict_name: bool = True,
) -> str:
    payload = compare_runs(
        db_path,
        baseline_id,
        candidate_id,
        strict_name=strict_name,
    )
    regressions = [r for r in payload["rows"] if r["change"] == "regressed"][:50]
    improvements = [r for r in payload["rows"] if r["change"] == "improved"][:50]

    env = Environment(autoescape=True)
    tmpl = env.from_string(COMPARE_TEMPLATE)
    return tmpl.render(
        baseline_id=baseline_id,
        candidate_id=candidate_id,
        baseline_name=payload["baseline"]["name"],
        candidate_name=payload["candidate"]["name"],
        warnings=payload["warnings"],
        summary=payload["summary_by_model"],
        regressions=regressions,
        improvements=improvements,
    )
