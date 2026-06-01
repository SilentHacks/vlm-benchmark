"""Image preprocessing utilities."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class ProcessedImage:
    image_id: str
    path: Path
    bytes: bytes
    mime_type: str
    width: int
    height: int


def preprocess_image(
    path: Path,
    image_id: str,
    *,
    max_long_edge: int = 1024,
    jpeg_quality: int = 85,
) -> ProcessedImage:
    with Image.open(path) as img:
        img = img.convert("RGB")
        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_long_edge:
            scale = max_long_edge / long_edge
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = new_w, new_h

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
        data = buf.getvalue()

    return ProcessedImage(
        image_id=image_id,
        path=path,
        bytes=data,
        mime_type="image/jpeg",
        width=w,
        height=h,
    )
