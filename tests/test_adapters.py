"""Adapter registry tests."""

import pytest

from vlm_bench.adapters.registry import create_adapter


def test_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        create_adapter("typo:model")
