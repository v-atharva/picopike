"""Raster exports: favicons and the social preview.

Rasters depend on the renderer, so they are exported on demand with Inkscape and are not
part of the drift check; the SVGs they are made from are.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from tools.logo.model import BrandSpec
from tools.logo.render import SOCIAL_SIZE, render_logo

ICO_SIZES = [(16, 16), (32, 32), (48, 48)]
APP_ICON_SIZES = (192, 512)
APPLE_TOUCH_SIZE = 180


def _inkscape() -> str:
    path = shutil.which("inkscape")
    if path is None:
        raise RuntimeError("Inkscape is required for raster exports: brew install --cask inkscape")
    return path


def rasterize(svg: Path, png: Path, width: int, height: int) -> None:
    """Render ``svg`` to a ``width`` x ``height`` PNG."""
    png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            _inkscape(),
            str(svg),
            "--export-type=png",
            f"--export-filename={png}",
            f"--export-width={width}",
            f"--export-height={height}",
        ],
        check=True,
        capture_output=True,
    )


def export_rasters(spec: BrandSpec, assets: Path) -> list[Path]:
    """Write the favicon set and ``social-preview.png`` next to their source SVGs."""
    favicon_dir = assets / "favicon"
    icon = assets / "icon.svg"
    written: list[Path] = []

    for size in APP_ICON_SIZES:
        target = favicon_dir / f"icon-{size}.png"
        rasterize(icon, target, size, size)
        written.append(target)

    with tempfile.TemporaryDirectory() as tmp:
        # iOS paints transparent corners black, so the touch icon gets the page background.
        opaque = Path(tmp) / "icon-opaque.svg"
        opaque.write_text(
            render_logo(spec.mark, spec.wordmark, spec.light, "icon", background=True)
        )
        target = favicon_dir / "apple-touch-icon.png"
        rasterize(opaque, target, APPLE_TOUCH_SIZE, APPLE_TOUCH_SIZE)
        written.append(target)

        large = Path(tmp) / "icon-256.png"
        rasterize(icon, large, 256, 256)
        target = favicon_dir / "favicon.ico"
        with Image.open(large) as image:
            image.save(target, sizes=ICO_SIZES)
        written.append(target)

    target = assets / "social-preview.png"
    rasterize(assets / "social-preview.svg", target, *SOCIAL_SIZE)
    written.append(target)
    return written
