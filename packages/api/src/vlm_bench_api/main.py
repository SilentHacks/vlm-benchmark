"""FastAPI application."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from vlm_bench.config import BenchmarkConfig
from vlm_bench.orchestrator import BenchmarkOrchestrator
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench.storage.models import InferenceRecord, MetricResult, Project, Run
from vlm_bench.validation import validate_config

DB_PATH = Path("data/vlm_bench.db")
ROOT = Path.cwd()
RUN_EVENTS: dict[str, list[dict]] = {}


app = FastAPI(title="VLM Benchmark API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)


class ProjectCreate(BaseModel):
    name: str
    config_yaml: str = ""


class RunCreate(BaseModel):
    project_id: str | None = None
    config_yaml: str | None = None
    config_path: str | None = None
    name: str = ""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/validate")
def validate_body(body: dict[str, Any]) -> dict[str, Any]:
    try:
        config = BenchmarkConfig.model_validate(body)
        errors = validate_config(config, ROOT)
        return {"valid": len(errors) == 0, "errors": errors}
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}


@app.get("/projects")
def list_projects() -> list[dict]:
    with session_scope(DB_PATH) as session:
        projects = session.query(Project).order_by(Project.created_at.desc()).all()
        return [
            {"id": p.id, "name": p.name, "created_at": p.created_at.isoformat()}
            for p in projects
        ]


@app.post("/projects")
def create_project(body: ProjectCreate) -> dict:
    pid = str(uuid.uuid4())[:12]
    with session_scope(DB_PATH) as session:
        p = Project(id=pid, name=body.name, config_yaml=body.config_yaml)
        session.add(p)
    return {"id": pid, "name": body.name}


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> dict:
    with session_scope(DB_PATH) as session:
        p = session.get(Project, project_id)
        if not p:
            raise HTTPException(404, "Project not found")
        return {
            "id": p.id,
            "name": p.name,
            "config_yaml": p.config_yaml,
            "created_at": p.created_at.isoformat(),
        }


@app.get("/runs")
def list_runs(limit: int = 20) -> list[dict]:
    with session_scope(DB_PATH) as session:
        runs = session.query(Run).order_by(Run.created_at.desc()).limit(limit).all()
        return [_run_to_dict(r) for r in runs]


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    with session_scope(DB_PATH) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        metrics = session.query(MetricResult).filter_by(run_id=run_id).all()
        inferences = session.query(InferenceRecord).filter_by(run_id=run_id).all()
        return {
            **_run_to_dict(run),
            "metrics": [_metric_to_dict(m) for m in metrics],
            "inferences": [_inf_to_dict(i) for i in inferences],
        }


@app.post("/runs")
def start_run(body: RunCreate, background_tasks: BackgroundTasks) -> dict:
    run_id = str(uuid.uuid4())[:12]
    config_path: Path | None = None
    if body.config_yaml:
        config = BenchmarkConfig.model_validate(yaml.safe_load(body.config_yaml))
    elif body.config_path:
        config_path = Path(body.config_path)
        if not config_path.is_absolute():
            config_path = ROOT / config_path
        config = BenchmarkConfig.from_yaml(config_path)
    else:
        raise HTTPException(400, "config_yaml or config_path required")

    errors = validate_config(config, config_path or ROOT)
    if errors:
        raise HTTPException(400, detail={"errors": errors})

    RUN_EVENTS[run_id] = []

    with session_scope(DB_PATH) as session:
        from vlm_bench.dataset import load_manifest

        try:
            rows = load_manifest(
                config.resolve_manifest_path(config_path),
                config.resolve_base_dir(config_path),
            )
            total = len(rows) * len(config.models)
        except Exception:
            total = len(config.models) * 3
        run = Run(
            id=run_id,
            project_id=body.project_id,
            name=body.name or config.name,
            status="pending",
            config_yaml=yaml.dump(config.model_dump()),
            progress_total=total,
        )
        session.add(run)

    background_tasks.add_task(_execute_run, run_id, config, config_path)
    return {"run_id": run_id, "status": "started"}


async def _execute_run(
    run_id: str,
    config: BenchmarkConfig,
    config_path: Path | None,
) -> None:
    events = RUN_EVENTS.setdefault(run_id, [])

    def on_progress(event: dict) -> None:
        events.append(event)

    try:
        orch = BenchmarkOrchestrator(
            config,
            config_path=config_path,
            db_path=DB_PATH,
            project_root=ROOT,
        )
        await orch.run(run_id=run_id, on_progress=on_progress)
    except Exception as e:
        events.append({"type": "error", "message": str(e)})
        with session_scope(DB_PATH) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
    events.append({"type": "done"})


@app.get("/runs/{run_id}/events")
async def run_events(run_id: str):
    async def event_generator():
        sent = 0
        while True:
            events = RUN_EVENTS.get(run_id, [])
            while sent < len(events):
                yield {"event": "message", "data": json.dumps(events[sent])}
                sent += 1
                if events[sent - 1].get("type") == "done":
                    return
            await asyncio.sleep(0.5)
            with session_scope(DB_PATH) as session:
                run = session.get(Run, run_id)
                if run and run.status in ("completed", "failed", "cancelled"):
                    if sent >= len(events):
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "done", "status": run.status}),
                        }
                    return

    return EventSourceResponse(event_generator())


@app.get("/thumbnails/{image_path:path}")
def serve_thumbnail(image_path: str) -> FileResponse:
    path = Path(image_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)


def _run_to_dict(run: Run) -> dict:
    raw = json.loads(run.aggregates_json or "{}")
    by_model = raw.get("by_model", raw)
    return {
        "id": run.id,
        "project_id": run.project_id,
        "name": run.name,
        "status": run.status,
        "progress_completed": run.progress_completed,
        "progress_total": run.progress_total,
        "aggregates": {"by_model": by_model},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def _metric_to_dict(m: MetricResult) -> dict:
    return {
        "image_id": m.image_id,
        "model_id": m.model_id,
        "score": m.score,
        "passed": m.passed,
        "details": json.loads(m.details_json or "{}"),
    }


def _inf_to_dict(i: InferenceRecord) -> dict:
    return {
        "image_id": i.image_id,
        "model_id": i.model_id,
        "raw_response": i.raw_response,
        "latency_ms": i.latency_ms,
        "cost_usd": i.cost_usd,
        "error": i.error,
        "cached": i.cached,
    }
