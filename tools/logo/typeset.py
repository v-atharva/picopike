"""Set text as vector outlines, so the logo renders the same without the font installed."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).resolve().parents[2] / "brand" / "fonts"
REGULAR = "Inter-Regular.ttf"
BOLD = "Inter-Bold.ttf"

PRINTABLE_ASCII = "".join(chr(code) for code in range(0x20, 0x7F))


@dataclass(frozen=True)
class Run:
    """A line of outlined text and the pen position after its last glyph."""

    svg: str
    end_x: float


@cache
def _font(name: str) -> Any:
    return TTFont(FONT_DIR / name)


def _glyph_names(font: Any, text: str) -> list[str]:
    cmap = font.getBestCmap()
    missing = sorted({ch for ch in text if ord(ch) not in cmap})
    if missing:
        raise ValueError(f"{font.reader.file.name} has no glyph for {missing!r}")
    return [cmap[ord(ch)] for ch in text]


def measure(font_name: str, text: str, *, size: float, letter_spacing: float = 0.0) -> float:
    """Width of ``text`` in canvas units, without tracking after the last glyph."""
    font = _font(font_name)
    scale = float(size / font["head"].unitsPerEm)
    advances = float(sum(font["hmtx"][name][0] for name in _glyph_names(font, text)))
    return advances * scale + letter_spacing * max(len(text) - 1, 0)


def set_text(
    font_name: str,
    text: str,
    *,
    size: float,
    x: float,
    baseline: float,
    fill: str,
    letter_spacing: float = 0.0,
) -> Run:
    """Outline ``text`` as SVG paths starting at ``(x, baseline)``.

    Pair kerning is not applied: the wordmark is set in tracked capitals, where it is
    negligible, and skipping it keeps the output independent of the font's GPOS tables.
    """
    font = _font(font_name)
    scale = size / font["head"].unitsPerEm
    tracking = letter_spacing / scale
    glyph_set = font.getGlyphSet()
    paths: list[str] = []
    pen_x = 0.0
    for name in _glyph_names(font, text):
        pen = SVGPathPen(glyph_set)
        glyph_set[name].draw(pen)
        if commands := pen.getCommands():
            paths.append(f'<path transform="translate({pen_x:.2f} 0)" d="{commands}"/>')
        pen_x += font["hmtx"][name][0] + tracking
    # Font units are y-up; flipping the y scale puts glyphs on the SVG baseline.
    svg = (
        f'<g fill="{fill}" transform="translate({x:.2f} {baseline:.2f}) '
        f'scale({scale:.6f} {-scale:.6f})">{"".join(paths)}</g>'
    )
    return Run(svg=svg, end_x=x + pen_x * scale)


def subset_font(source: Path, target: Path) -> None:
    """Keep printable ASCII only, so the bundled fonts stay small."""
    options = Options()
    options.hinting = False
    options.layout_features = ["kern"]
    options.name_IDs = ["*"]  # keep copyright and licence records
    subsetter = Subsetter(options)
    subsetter.populate(text=PRINTABLE_ASCII)
    font = TTFont(source)
    subsetter.subset(font)
    target.parent.mkdir(parents=True, exist_ok=True)
    font.save(target)
