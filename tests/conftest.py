"""Pytest fixtures."""

from pathlib import Path

import pytest
from PIL import Image, ImageDraw


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
IMAGES_DIR = FIXTURES_DIR / "images"


@pytest.fixture(scope="session", autouse=True)
def generate_fixture_images():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    colors = [
        ("img_001", (220, 50, 50)),
        ("img_002", (50, 200, 50)),
        ("img_003", (200, 100, 50)),
    ]
    for name, color in colors:
        path = IMAGES_DIR / f"{name}.png"
        if not path.exists():
            img = Image.new("RGB", (256, 256), color)
            draw = ImageDraw.Draw(img)
            draw.rectangle([64, 64, 192, 192], fill=(255, 255, 255))
            draw.text((80, 120), name, fill=(0, 0, 0))
            img.save(path)
    yield


@pytest.fixture
def temp_db(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def root():
    return Path(__file__).resolve().parents[1]
