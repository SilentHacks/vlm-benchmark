"""Shared run results loading for CLI and API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vlm_bench.storage.db import session_scope
from vlm_bench.storage.models import MetricResult, Run


@dataclass
class RunResultsDTO:
    run: Run
    metrics: list[MetricResult]
    aggregates: dict[str, Any]


def load_run_results(db_path: str | Path, run_id: str) -> RunResultsDTO:
    with session_scope(db_path) as session:
        run = session.get(Run, run_id)
        if not run:
            raise KeyError(f"Run not found: {run_id}")
        metrics = session.query(MetricResult).filter_by(run_id=run_id).all()
        import json

        raw = json.loads(run.aggregates_json or "{}")
        by_model = raw.get("by_model", raw)
        return RunResultsDTO(run=run, metrics=metrics, aggregates={"by_model": by_model})
