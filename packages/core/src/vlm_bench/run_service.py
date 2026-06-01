"""Run lifecycle helpers shared by API and orchestrator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from vlm_bench.config import BenchmarkConfig
from vlm_bench.storage.models import Run


def create_pending_run(
    session: Session,
    *,
    run_id: str,
    name: str,
    config_yaml: str,
    progress_total: int,
    project_id: str | None = None,
) -> Run:
    run = Run(
        id=run_id,
        project_id=project_id,
        name=name,
        status="pending",
        config_yaml=config_yaml,
        progress_total=progress_total,
    )
    session.add(run)
    session.flush()
    return run


def begin_run(
    session: Session,
    run_id: str,
    config: BenchmarkConfig,
    *,
    config_yaml: str,
    progress_total: int,
) -> Run:
    existing = session.get(Run, run_id)
    if existing is not None:
        run = existing
        run.name = config.name
        run.status = "running"
        run.config_yaml = config_yaml
        run.progress_completed = 0
        run.progress_total = progress_total
        run.aggregates_json = "{}"
        run.finished_at = None
    else:
        run = Run(
            id=run_id,
            name=config.name,
            status="running",
            config_yaml=config_yaml,
            progress_completed=0,
            progress_total=progress_total,
        )
        session.add(run)
    session.flush()
    return run


def finalize_run(
    session: Session,
    run: Run,
    *,
    status: str,
    aggregates: dict[str, Any],
    progress_completed: int,
) -> None:
    run.status = status
    run.aggregates_json = json.dumps({"by_model": aggregates})
    run.finished_at = datetime.now(timezone.utc)
    run.progress_completed = progress_completed
    session.flush()
