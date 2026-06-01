#!/usr/bin/env python3
"""Generate minimal fixture PNG images."""

import json
import struct
import zlib
from pathlib import Path


def write_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b""
    r, g, b = rgb
    for _ in range(height):
        raw += b"\x00" + bytes([r, g, b]) * width

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    images = root / "fixtures" / "images"
    images.mkdir(parents=True, exist_ok=True)

    specs = [
        ("img_001.png", (220, 50, 50), "defect"),
        ("img_002.png", (50, 180, 80), "ok"),
        ("img_003.png", (50, 80, 220), "defect"),
    ]
    rows = []
    for fname, color, label in specs:
        write_png(images / fname, 32, 32, color)
        image_id = fname.replace(".png", "")
        rows.append(
            {
                "image_id": image_id,
                "path": f"images/{fname}",
                "expected_class": label,
            }
        )

    manifest = root / "fixtures" / "manifest.jsonl"
    with manifest.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"Generated {len(rows)} fixtures -> {manifest}")


if __name__ == "__main__":
    main()
