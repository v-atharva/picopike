"""The exploration round: 50 deterministic concepts, plus a contact sheet.

The option lists and seeds are frozen so concept numbers are stable identifiers; concept 16
is the one the brand spec was built from. Add new rounds instead of reshuffling this one.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import cast, get_args

from tools.logo.model import (
    Container,
    Impact,
    Layout,
    MarkSpec,
    Palette,
    PikeStyle,
    Target,
    WordmarkSpec,
    WordmarkStyle,
)
from tools.logo.render import render_logo

COUNT = 50

PALETTES: dict[str, Palette] = {
    "navy-amber": Palette(ink="#0F172A", accent="#F59E0B", bg="#FFFFFF", tint="#F1F5F9"),
    "mono-black": Palette(ink="#111111", accent="#111111", bg="#FFFFFF", tint="#F0F0F0"),
    "mono-white": Palette(ink="#F8FAFC", accent="#F8FAFC", bg="#0B1220", tint="#16203A"),
    "night-amber": Palette(ink="#E2E8F0", accent="#F59E0B", bg="#0B1220", tint="#16203A"),
    "teal-coral": Palette(ink="#0B3B3C", accent="#FF6B5A", bg="#FFFFFF", tint="#E6F4F1"),
    "violet-lime": Palette(ink="#2E1065", accent="#84CC16", bg="#FFFFFF", tint="#F3EFFF"),
    "graphite-red": Palette(ink="#1F2937", accent="#EF4444", bg="#FFFFFF", tint="#F3F4F6"),
    "night-cyan": Palette(ink="#CFE8FF", accent="#22D3EE", bg="#06121F", tint="#0D2238"),
}


def _balanced[T](options: Sequence[T], n: int, seed: int) -> list[T]:
    """``n`` picks that use every option about equally often, in a seeded-shuffled order."""
    rng = random.Random(seed)
    picks: list[T] = []
    while len(picks) < n:
        chunk = list(options)
        rng.shuffle(chunk)
        picks += chunk
    return picks[:n]


@dataclass(frozen=True)
class Concept:
    number: int
    mark: MarkSpec
    wordmark: WordmarkSpec
    palette_name: str
    layout: Layout

    @property
    def palette(self) -> Palette:
        return PALETTES[self.palette_name]

    @property
    def filename(self) -> str:
        m = self.mark
        parts = (
            f"{self.number:02d}",
            m.target,
            m.pike,
            self.palette_name,
            m.container,
            self.layout,
        )
        return "-".join(parts) + ".svg"

    @property
    def caption(self) -> str:
        m = self.mark
        parts = (m.target, m.pike, f"{m.angle}°", self.palette_name, m.container, self.layout)
        return " · ".join(parts)


def plan() -> list[Concept]:
    """The fixed list of concepts. Order of the seeded draws below must not change."""
    targets = _balanced(list(get_args(Target)), COUNT, 1)
    pikes = _balanced(list(get_args(PikeStyle)), COUNT, 2)
    angles = _balanced([22, 30, 38, 46, 54], COUNT, 3)
    impacts = _balanced(list(get_args(Impact)), COUNT, 4)
    palettes = _balanced(list(PALETTES), COUNT, 5)
    containers = _balanced(list(get_args(Container)), COUNT, 6)
    layouts = _balanced(
        cast("list[Layout]", ["horizontal", "horizontal", "stacked", "icon"]), COUNT, 7
    )
    styles = _balanced(list(get_args(WordmarkStyle)), COUNT, 8)
    flips = _balanced([False, False, True], COUNT, 9)
    return [
        Concept(
            number=i + 1,
            mark=MarkSpec(
                target=targets[i],
                pike=pikes[i],
                angle=angles[i],
                impact=impacts[i],
                flip=flips[i],
                container=containers[i],
            ),
            wordmark=WordmarkSpec(style=styles[i]),
            palette_name=palettes[i],
            layout=layouts[i],
        )
        for i in range(COUNT)
    ]


def render_concept(concept: Concept) -> str:
    """One concept as a full SVG document on its own background."""
    return render_logo(
        concept.mark, concept.wordmark, concept.palette, concept.layout, background=True
    )


_SHEET_CSS = (
    "body{margin:0;padding:24px 16px;background:#e5e7eb;"
    "font:13px/1.4 system-ui,sans-serif;color:#111}"
    "h1{font-size:18px;margin:0 0 16px}"
    ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}"
    "figure{margin:0;background:#fff;border-radius:10px;padding:10px;box-shadow:0 1px 3px #0002}"
    "img{width:100%;height:170px;object-fit:contain;border-radius:6px}"
    "figcaption{margin-top:6px;color:#444;font-size:11px}"
)


def write_round(out_dir: Path) -> list[Path]:
    """Write every concept SVG and an ``index.html`` contact sheet into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    concepts = plan()
    written: list[Path] = []
    for concept in concepts:
        path = out_dir / concept.filename
        path.write_text(render_concept(concept))
        written.append(path)
    cards = "\n".join(
        f'<figure><img src="{escape(c.filename)}" alt="concept {c.number}">'
        f"<figcaption><b>{c.number:02d}</b> {escape(c.caption)}</figcaption></figure>"
        for c in concepts
    )
    index = out_dir / "index.html"
    index.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>PicoPike logo concepts, round 2</title><style>{_SHEET_CSS}</style></head><body>"
        f"<h1>PicoPike logo concepts: round 2 ({COUNT})</h1>"
        f'<div class="grid">{cards}</div></body></html>\n'
    )
    return [*written, index]
