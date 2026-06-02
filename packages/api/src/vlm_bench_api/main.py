"""FastAPI application."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import yaml
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from vlm_bench_api.schemas import (
    RunCompareResponse,
    RunDetail,
    RunResults,
    ValidateRequest,
    ValidateResponse,
)
from sse_starlette.sse import EventSourceResponse

from vlm_bench.config import BenchmarkConfig
from vlm_bench.compare import compare_runs
from vlm_bench.paths import resolve_paths
from vlm_bench.run_service import create_pending_run
from vlm_bench.orchestrator import BenchmarkOrchestrator
from vlm_bench.run_checks import check_fail_under
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench.storage.models import InferenceRecord, MetricResult, Project, Run
from vlm_bench.validation import validate_config
from vlm_bench_api.serializers import (
    run_detail_payload,
    run_results_payload,
    run_to_dict,
)

DB_PATH = Path("data/vlm_bench.db")
ROOT = Path.cwd()
RUN_EVENTS: dict[str, list[dict]] = {}
ACTIVE_ORCHESTRATORS: dict[str, BenchmarkOrchestrator] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db(DB_PATH)
    yield


app = FastAPI(title="VLM Benchmark API", version="0.3.0", lifespan=lifespan)
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


@app.post("/validate", response_model=ValidateResponse)
def validate_body(body: ValidateRequest) -> ValidateResponse:
    try:
        errors = validate_config(body, ROOT)
        return ValidateResponse(valid=len(errors) == 0, errors=errors)
    except Exception as e:
        return ValidateResponse(valid=False, errors=[str(e)])


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
        return [run_to_dict(r) for r in runs]


@app.get("/runs/compare", response_model=RunCompareResponse)
def compare_run_pair(
    baseline: str,
    candidate: str,
    strict_name: bool = True,
) -> RunCompareResponse:
    try:
        payload = compare_runs(
            DB_PATH,
            baseline,
            candidate,
            strict_name=strict_name,
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return RunCompareResponse.model_validate(payload)


@app.get("/runs/{run_id}/results", response_model=RunResults)
def get_run_results(run_id: str) -> RunResults:
    with session_scope(DB_PATH) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        metrics = session.query(MetricResult).filter_by(run_id=run_id).all()
        return RunResults.model_validate(run_results_payload(run, metrics))


@app.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str) -> RunDetail:
    with session_scope(DB_PATH) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        metrics = session.query(MetricResult).filter_by(run_id=run_id).all()
        inferences = session.query(InferenceRecord).filter_by(run_id=run_id).all()
        return RunDetail.model_validate(run_detail_payload(run, metrics, inferences))


@app.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict:
    orch = ACTIVE_ORCHESTRATORS.get(run_id)
    if orch:
        orch.cancel()
    with session_scope(DB_PATH) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        if run.status in ("pending", "running"):
            run.status = "cancelled"
    return {"run_id": run_id, "status": "cancelled"}


@app.post("/runs")
def start_run(body: RunCreate, background_tasks: BackgroundTasks) -> dict:
    run_id = str(uuid.uuid4())[:12]
    config_path: Path | None = None
    if body.config_yaml:
        config = BenchmarkConfig.model_validate(yaml.safe_load(body.config_yaml))
    elif body.config_path:
        try:
            config_path = _resolve_under_root(Path(body.config_path), status=400)
        except HTTPException:
            raise
        except (OSError, ValueError) as e:
            raise HTTPException(400, "Invalid config_path") from e
        config = BenchmarkConfig.from_yaml(config_path)
    else:
        raise HTTPException(400, "config_yaml or config_path required")

    if config.metric.type in ("custom_plugin", "plugin"):
        raise HTTPException(
            400,
            "custom_plugin metrics are only supported via the CLI (not HTTP runs)",
        )

    errors = validate_config(config, config_path or ROOT)
    if errors:
        raise HTTPException(400, detail={"errors": errors})

    RUN_EVENTS[run_id] = []

    with session_scope(DB_PATH) as session:
        from vlm_bench.dataset import load_manifest

        try:
            manifest_path, base_dir = resolve_paths(
                config, config_path=config_path, project_root=ROOT
            )
            rows = load_manifest(manifest_path, base_dir)
            total = len(rows) * len(config.models)
        except Exception:
            total = len(config.models) * 3
        create_pending_run(
            session,
            run_id=run_id,
            name=body.name or config.name,
            config_yaml=yaml.dump(config.model_dump()),
            progress_total=total,
            project_id=body.project_id,
        )

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

    orch = BenchmarkOrchestrator(
        config,
        config_path=config_path,
        db_path=DB_PATH,
        project_root=ROOT,
    )
    ACTIVE_ORCHESTRATORS[run_id] = orch
    try:
        result = await orch.run(run_id=run_id, on_progress=on_progress)
        passed, best, threshold = check_fail_under(config, result.get("aggregates", {}))
        if not passed and threshold is not None:
            events.append(
                {
                    "type": "fail_under",
                    "best_score": best,
                    "threshold": threshold,
                }
            )
            with session_scope(DB_PATH) as session:
                run = session.get(Run, run_id)
                if run:
                    run.status = "failed"
    except Exception as e:
        events.append({"type": "error", "message": str(e)})
        with session_scope(DB_PATH) as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "failed"
    finally:
        ACTIVE_ORCHESTRATORS.pop(run_id, None)
        events.append({"type": "done"})
        RUN_EVENTS.pop(run_id, None)


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
                    RUN_EVENTS.pop(run_id, None)
                    return

    return EventSourceResponse(event_generator())


def _resolve_under_root(path: Path, *, status: int = 404) -> Path:
    root = ROOT.resolve()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise HTTPException(status, "Path not allowed")
    return resolved


@app.get("/thumbnails/{image_path:path}")
def serve_thumbnail(image_path: str) -> FileResponse:
    try:
        path = _resolve_under_root(Path(image_path))
    except HTTPException:
        raise
    except (OSError, ValueError):
        raise HTTPException(404, "Image not found") from None
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)
