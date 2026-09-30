"""Typed description of a logo: what the mark shows, how it is coloured, how it is set."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Target = Literal["bot", "rack", "datacenter", "chip", "cyclops", "promptbot"]
PikeStyle = Literal["spear", "needle", "lance", "bolt"]
Impact = Literal["cracks", "ring", "none"]
Container = Literal["none", "circle", "square", "shield"]
Layout = Literal["horizontal", "stacked", "icon"]
WordmarkStyle = Literal["light-bold", "caps", "mono", "slash"]


@dataclass(frozen=True)
class Palette:
    """Colour tokens. ``tint`` fills the container; ``bg`` is the canvas behind it."""

    ink: str
    accent: str
    bg: str
    tint: str


@dataclass(frozen=True)
class MarkSpec:
    """The pictogram: a pike striking a target at an angle."""

    target: Target
    pike: PikeStyle
    angle: int
    impact: Impact
    flip: bool
    container: Container


@dataclass(frozen=True)
class WordmarkSpec:
    style: WordmarkStyle


@dataclass(frozen=True)
class BrandSpec:
    """A complete, buildable logo definition."""

    name: str
    concept: int
    mark: MarkSpec
    wordmark: WordmarkSpec
    light: Palette
    dark: Palette


def load_spec(path: Path) -> BrandSpec:
    """Read a spec from JSON (see ``brand/logo.spec.json``)."""
    raw = json.loads(path.read_text())
    return BrandSpec(
        name=raw["name"],
        concept=raw["concept"],
        mark=MarkSpec(**raw["mark"]),
        wordmark=WordmarkSpec(**raw["wordmark"]),
        light=Palette(**raw["palettes"]["light"]),
        dark=Palette(**raw["palettes"]["dark"]),
    )
