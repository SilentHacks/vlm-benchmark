"""Response parsing helpers."""

from __future__ import annotations

import json
import re
from typing import Any

from jsonpath_ng import parse as jsonpath_parse

from vlm_bench.config import MetricParseConfig


def parse_response(response: str, parse_cfg: MetricParseConfig | None) -> Any:
    if parse_cfg is None or parse_cfg.mode == "raw":
        return response.strip()

    if parse_cfg.mode == "json":
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown fences
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
            if match:
                data = json.loads(match.group(1))
            else:
                match = re.search(r"\{[\s\S]*\}", response)
                if match:
                    data = json.loads(match.group(0))
                else:
                    return response.strip()
        if parse_cfg.path:
            matches = jsonpath_parse(parse_cfg.path).find(data)
            if matches:
                return matches[0].value
            return None
        return data

    if parse_cfg.mode == "regex" and parse_cfg.pattern:
        match = re.search(parse_cfg.pattern, response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(parse_cfg.group)
        return None

    return response.strip()


def normalize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip().lower()
