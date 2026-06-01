"""Dataset manifest loading."""

from __future__ import annotations

import json
from pathlib import Path

from vlm_bench.config import ManifestRow


def load_manifest(path: str | Path, base_dir: str | Path | None = None) -> list[ManifestRow]:
    path = Path(path)
    base = Path(base_dir) if base_dir else path.parent
    rows: list[ManifestRow] = []

    if path.suffix == ".jsonl":
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(ManifestRow.model_validate(json.loads(line)))
    elif path.suffix == ".json":
        with path.open() as f:
            data = json.load(f)
            items = data if isinstance(data, list) else data.get("items", [])
            rows = [ManifestRow.model_validate(item) for item in items]
    else:
        raise ValueError(f"Unsupported manifest format: {path.suffix}")

    for row in rows:
        img_path = Path(row.path)
        if not img_path.is_absolute():
            row.path = str((base / img_path).resolve())
        else:
            row.path = str(img_path.resolve())

    return rows
