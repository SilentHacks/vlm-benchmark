"""VLM Benchmark core library."""

from vlm_bench.config import BenchmarkConfig, ManifestRow, load_config
from vlm_bench.dataset import load_manifest
from vlm_bench.orchestrator import BenchmarkOrchestrator
from vlm_bench.validation import validate_config

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "BenchmarkConfig",
    "BenchmarkOrchestrator",
    "ManifestRow",
    "load_config",
    "load_manifest",
    "validate_config",
]
