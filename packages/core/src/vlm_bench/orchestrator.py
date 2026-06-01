"""Benchmark orchestrator with async parallelism and caching."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from vlm_bench.adapters.registry import create_adapter
from vlm_bench.cache import InferenceCache, cache_key
from vlm_bench.config import BenchmarkConfig, ManifestRow
from vlm_bench.cost import aggregate_run_stats
from vlm_bench.dataset import load_manifest
from vlm_bench.image import ProcessedImage, preprocess_image
from vlm_bench.metrics.engine import MetricEngine
from vlm_bench.pricing import CostLatencyTracker, PricingTable
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench.storage.models import InferenceRecord, MetricResult, Run


ProgressCallback = Callable[[dict[str, Any]], None]


class BenchmarkOrchestrator:
    def __init__(
        self,
        config: BenchmarkConfig,
        *,
        config_path: Path | None = None,
        db_path: str | Path | None = None,
        db_session: Session | None = None,
        pricing: PricingTable | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.db_path = Path(db_path) if db_path else Path("data/vlm_bench.db")
        self._external_session = db_session
        self.pricing = pricing or PricingTable.default()
        self.project_root = project_root or (config_path.parent if config_path else Path.cwd())
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def run(
        self,
        run_id: str | None = None,
        model_filter: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        if self._external_session is not None:
            return await self._run_inner(
                self._external_session,
                run_id=run_id,
                model_filter=model_filter,
                on_progress=on_progress,
                commit_externally=False,
            )

        init_db(self.db_path)
        with session_scope(self.db_path) as session:
            return await self._run_inner(
                session,
                run_id=run_id,
                model_filter=model_filter,
                on_progress=on_progress,
                commit_externally=True,
            )

    async def _run_inner(
        self,
        session: Session,
        *,
        run_id: str | None,
        model_filter: list[str] | None,
        on_progress: ProgressCallback | None,
        commit_externally: bool,
    ) -> dict[str, Any]:
        errors = self._validate()
        if errors:
            raise ValueError("; ".join(errors))

        run_id = run_id or str(uuid.uuid4())[:12]
        manifest_path = self.config.resolve_manifest_path(self.config_path)
        base_dir = self.config.resolve_base_dir(self.config_path)
        rows = load_manifest(manifest_path, base_dir)
        models = model_filter or self.config.models
        total_tasks = len(rows) * len(models)

        run = Run(
            id=run_id,
            name=self.config.name,
            status="running",
            config_yaml=self._config_yaml(),
            progress_completed=0,
            progress_total=total_tasks,
        )
        session.add(run)
        session.flush()

        cache = (
            InferenceCache(session, ttl_hours=self.config.execution.cache_ttl_hours)
            if self.config.execution.cache
            else None
        )
        metric_engine = MetricEngine(self.config, self.project_root)
        tracker = CostLatencyTracker(pricing=self.pricing)

        processed: dict[str, ProcessedImage] = {}
        for row in rows:
            processed[row.image_id] = preprocess_image(
                Path(row.path),
                row.image_id,
                max_long_edge=self.config.image.max_long_edge,
                jpeg_quality=self.config.image.jpeg_quality,
            )

        semaphores = {m: asyncio.Semaphore(self.config.execution.max_concurrency) for m in models}
        completed = 0
        metric_records: list[dict[str, Any]] = []
        inference_out: list[dict[str, Any]] = []
        lock = asyncio.Lock()

        async def process_task(row: ManifestRow, model_id: str) -> None:
            nonlocal completed
            if self._cancelled:
                return

            adapter = create_adapter(
                model_id,
                pricing=self.pricing,
                timeout=self.config.execution.timeout_seconds,
            )
            image = processed[row.image_id]
            system = self._render_prompt(self.config.prompts.system, row)
            user = self._render_prompt(self.config.prompts.user, row)
            key = cache_key(model_id, system, user, image.bytes)

            result = cache.get(key) if cache else None
            async with semaphores[model_id]:
                if result is None:
                    for attempt in range(self.config.execution.retries + 1):
                        result = await adapter.complete(system=system, user=user, image=image)
                        if not result.error:
                            break
                        if attempt < self.config.execution.retries:
                            await asyncio.sleep(2**attempt)
                    if cache and result and not result.error:
                        cache.put(key, result)

            if result is None:
                return

            tracker.record(
                model_id,
                usage=result.usage if not result.error else None,
                latency_ms=result.latency_ms,
                error=bool(result.error),
            )

            response_text = result.raw_response if not result.error else ""
            metric_score = metric_engine.score(
                image_id=row.image_id,
                response=response_text,
                ground_truth=row,
                prompt_system=system,
                prompt_user=user,
            )

            session.add(
                InferenceRecord(
                    run_id=run_id,
                    image_id=row.image_id,
                    model_id=model_id,
                    raw_response=result.raw_response,
                    parsed_response=result.parsed_response,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=result.latency_ms,
                    cost_usd=result.cost_usd,
                    error=result.error,
                    cached=result.cached,
                )
            )
            session.add(
                MetricResult(
                    run_id=run_id,
                    image_id=row.image_id,
                    model_id=model_id,
                    score=metric_score.score,
                    passed=metric_score.passed,
                    details_json=json.dumps(metric_score.details),
                )
            )

            inference_out.append(
                {
                    "image_id": row.image_id,
                    "model_id": model_id,
                    "raw_response": result.raw_response,
                    "latency_ms": result.latency_ms,
                    "cost_usd": result.cost_usd,
                    "error": result.error,
                    "cached": result.cached,
                }
            )
            metric_records.append(
                {
                    "model_id": model_id,
                    "image_id": row.image_id,
                    "score": metric_score.score,
                    "passed": metric_score.passed,
                    "latency_ms": result.latency_ms,
                    "cost_usd": result.cost_usd,
                    "error": result.error,
                }
            )

            async with lock:
                completed += 1
                run.progress_completed = completed
                session.flush()
                if on_progress:
                    on_progress(
                        {
                            "type": "progress",
                            "run_id": run_id,
                            "completed": completed,
                            "total": total_tasks,
                            "model_id": model_id,
                            "image_id": row.image_id,
                            "score": metric_score.score,
                            "passed": metric_score.passed,
                            "error": result.error,
                        }
                    )

            if hasattr(adapter, "close"):
                await adapter.close()

        await asyncio.gather(*[process_task(row, m) for row in rows for m in models])

        aggregates = aggregate_run_stats(metric_records)
        run.status = "cancelled" if self._cancelled else "completed"
        run.aggregates_json = json.dumps({"by_model": aggregates})
        run.finished_at = datetime.now(timezone.utc)
        run.progress_completed = completed
        session.flush()

        if on_progress:
            on_progress(
                {"type": "complete", "run_id": run_id, "aggregates": {"by_model": aggregates}}
            )

        if commit_externally:
            session.commit()

        return {
            "run_id": run_id,
            "status": run.status,
            "aggregates": {"by_model": aggregates},
            "inferences": inference_out,
            "metric_results": [
                {
                    "image_id": r["image_id"],
                    "model_id": r["model_id"],
                    "score": r["score"],
                    "passed": r["passed"],
                }
                for r in metric_records
            ],
        }

    def _validate(self) -> list[str]:
        errors: list[str] = []
        manifest_path = self.config.resolve_manifest_path(self.config_path)
        if not manifest_path.exists():
            errors.append(f"Manifest not found: {manifest_path}")
            return errors
        try:
            rows = load_manifest(manifest_path, self.config.resolve_base_dir(self.config_path))
            if not rows:
                errors.append("Manifest is empty")
            for row in rows:
                if not Path(row.path).exists():
                    errors.append(f"Image not found: {row.path} (image_id={row.image_id})")
        except Exception as e:
            errors.append(f"Failed to load manifest: {e}")
        if not self.config.models:
            errors.append("No models configured")
        return errors

    def _config_yaml(self) -> str:
        import yaml

        return yaml.dump(self.config.model_dump(), default_flow_style=False)

    @staticmethod
    def _render_prompt(template: str, row: ManifestRow) -> str:
        if not template:
            return ""
        result = template.replace("{{image_filename}}", Path(row.path).name)
        result = result.replace("{{image_id}}", row.image_id)
        for key, value in row.metadata.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        extra = row.model_dump(exclude={"image_id", "path", "metadata"})
        for key, value in extra.items():
            if value is not None:
                result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
