"""HTML report export."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from vlm_bench.storage.db import session_scope
from vlm_bench.storage.models import MetricResult, Run

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
    <tr><th>Model</th><th>Score</th><th>Correct/Total</th><th>Cost USD</th><th>Errors</th></tr>
    {% for row in leaderboard %}
    <tr>
      <td>{{ row.model_id }}</td>
      <td>{{ "%.4f"|format(row.score) }}</td>
      <td>{{ row.correct }}/{{ row.total }}</td>
      <td>${{ "%.4f"|format(row.cost) }}</td>
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


def render_html_report(run_id: str, db_path: str | Path) -> str:
    with session_scope(db_path) as session:
        run = session.get(Run, run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")
        raw_agg = json.loads(run.aggregates_json or "{}")
        by_model = raw_agg.get("by_model", raw_agg)
        metrics = session.query(MetricResult).filter_by(run_id=run_id).all()

    leaderboard = []
    for model_id, agg in by_model.items():
        leaderboard.append(
            {
                "model_id": model_id,
                "score": agg.get("primary_score", 0),
                "correct": agg.get("correct", 0),
                "total": agg.get("total", 0),
                "cost": agg.get("cost_usd", 0),
                "errors": agg.get("errors", 0),
            }
        )
    leaderboard.sort(key=lambda x: x["score"], reverse=True)

    tmpl = Template(REPORT_TEMPLATE)
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
