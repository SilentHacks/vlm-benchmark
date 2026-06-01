"""CLI export tests."""

from pathlib import Path

import pytest

from vlm_bench.config import BenchmarkConfig
from vlm_bench.orchestrator import BenchmarkOrchestrator
from vlm_bench.storage.db import init_db, session_scope
from vlm_bench_cli.export import render_html_report

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "example-bench.yaml"


@pytest.mark.asyncio
async def test_html_export_autoescapes(tmp_path):
    db = tmp_path / "bench.db"
    init_db(db)
    cfg = BenchmarkConfig.from_yaml(CONFIG_PATH)
    cfg.name = "<script>alert('xss')</script>"

    with session_scope(db) as session:
        orch = BenchmarkOrchestrator(
            cfg,
            config_path=CONFIG_PATH,
            db_session=session,
            project_root=ROOT,
        )
        result = await orch.run()

    html = render_html_report(result["run_id"], db)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
