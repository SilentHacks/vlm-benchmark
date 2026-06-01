"""Typer CLI for vlm-bench."""

from __future__ import annotations

import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from vlm_bench.config import load_config
from vlm_bench.orchestrator import BenchmarkOrchestrator
from vlm_bench.run_checks import check_fail_under
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench.storage.models import MetricResult, Run
from vlm_bench.validation import validate_config

app = typer.Typer(name="vlm-bench", help="VLM Benchmark — compare vision models on datasets")
console = Console()


@app.command()
def validate(
    config: Path = typer.Option(..., "-c", "--config", help="Benchmark YAML config"),
) -> None:
    """Validate a benchmark configuration file."""
    try:
        cfg = load_config(config)
        errors = validate_config(cfg, config.resolve())
        if errors:
            for err in errors:
                console.print(f"[red]✗[/red] {err}")
            raise typer.Exit(1)
        console.print(f"[green]✓[/green] Config valid: {cfg.name}")
        console.print(f"  Models: {', '.join(cfg.models)}")
        console.print(f"  Metric: {cfg.metric.type}")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Invalid config:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def run(
    config: Path = typer.Option(..., "-c", "--config", help="Benchmark YAML config"),
    models: Optional[str] = typer.Option(None, "--models", help="Comma-separated model IDs"),
    db: Path = typer.Option(Path("data/vlm_bench.db"), "--db", help="SQLite database path"),
    fail_under: Optional[float] = typer.Option(
        None, "--fail-under", help="Exit 1 if primary metric below threshold"
    ),
) -> None:
    """Run a benchmark."""
    cfg = load_config(config)
    errors = validate_config(cfg, config.resolve())
    if errors:
        for err in errors:
            console.print(f"[red]✗[/red] {err}")
        raise typer.Exit(1)

    init_db(db)
    model_filter = [m.strip() for m in models.split(",")] if models else None
    root = config.resolve().parent.parent
    orch = BenchmarkOrchestrator(
        cfg,
        config_path=config.resolve(),
        db_path=db,
        project_root=root,
    )

    def on_progress(event: dict) -> None:
        if event.get("type") == "progress":
            console.print(
                f"  [{event['completed']}/{event['total']}] "
                f"{event.get('image_id')} @ {event.get('model_id')}"
            )

    result = asyncio.run(orch.run(model_filter=model_filter, on_progress=on_progress))
    run_id = result["run_id"]
    console.print(f"[green]✓[/green] Run complete: {run_id}")

    if fail_under is not None:
        cfg = cfg.model_copy(update={"fail_under": fail_under})
    passed, best, threshold = check_fail_under(cfg, result.get("aggregates", {}))
    if threshold is not None:
        if not passed:
            console.print(f"[red]✗[/red] Best score {best:.4f} below threshold {threshold}")
            raise typer.Exit(1)
        console.print(f"[green]✓[/green] Best score {best:.4f} meets threshold {threshold}")


@app.command()
def results(
    run_id: str = typer.Argument(..., help="Run ID"),
    format: str = typer.Option("table", "--format", "-f", help="table|json|csv"),
    db: Path = typer.Option(Path("data/vlm_bench.db"), "--db"),
) -> None:
    """Show results for a run."""
    init_db(db)
    with session_scope(db) as session:
        run = session.get(Run, run_id)
        if not run:
            console.print(f"[red]Run not found: {run_id}[/red]")
            raise typer.Exit(1)
        raw_agg = json.loads(run.aggregates_json or "{}")
        aggregates = raw_agg.get("by_model", raw_agg)
        metrics = session.query(MetricResult).filter_by(run_id=run_id).all()

    if format == "json":
        console.print(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": run.status,
                    "aggregates": aggregates,
                    "metrics": [
                        {
                            "image_id": m.image_id,
                            "model_id": m.model_id,
                            "score": m.score,
                            "passed": m.passed,
                        }
                        for m in metrics
                    ],
                },
                indent=2,
            )
        )
        return

    if format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["model_id", "primary_score", "correct", "total", "cost_usd", "errors"])
        for model_id, agg in aggregates.items():
            writer.writerow(
                [
                    model_id,
                    agg.get("primary_score", 0),
                    agg.get("correct", 0),
                    agg.get("total", 0),
                    agg.get("cost_usd", 0),
                    agg.get("errors", 0),
                ]
            )
        return

    table = Table(title=f"Results: {run_id}")
    table.add_column("Model")
    table.add_column("Score")
    table.add_column("Correct/Total")
    table.add_column("P50 ms")
    table.add_column("Cost USD")
    table.add_column("Errors")
    for model_id, agg in sorted(
        aggregates.items(), key=lambda x: x[1].get("primary_score", 0), reverse=True
    ):
        lat = agg.get("latency_ms", {})
        table.add_row(
            model_id,
            f"{agg.get('primary_score', 0):.4f}",
            f"{agg.get('correct', 0)}/{agg.get('total', 0)}",
            f"{lat.get('p50', 0):.0f}",
            f"{agg.get('cost_usd', 0):.4f}",
            str(agg.get("errors", 0)),
        )
    console.print(table)


@app.command()
def export(
    run_id: str = typer.Argument(..., help="Run ID"),
    out: Path = typer.Option(..., "--out", "-o", help="Output HTML path"),
    db: Path = typer.Option(Path("data/vlm_bench.db"), "--db"),
) -> None:
    """Export run results as HTML report."""
    from vlm_bench_cli.export import render_html_report

    init_db(db)
    html = render_html_report(run_id, db)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    console.print(f"[green]✓[/green] Exported to {out}")


if __name__ == "__main__":
    app()
