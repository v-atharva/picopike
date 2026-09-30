"""Drawing primitives for the mark, all in a 100x100-ish local coordinate space.

Targets are the things being struck; each returns its SVG and the impact point on its face.
``paper`` is the colour behind the mark (used for cut-outs and pike halos), so the mark reads
on any container fill.
"""

# ruff: noqa: E501  (SVG path and attribute strings are clearer unbroken)

from __future__ import annotations

import math
from collections.abc import Callable

from tools.logo.model import Impact, PikeStyle, Target

BBox = tuple[float, float, float, float]
TargetFn = Callable[[str, str, str], tuple[str, tuple[int, int]]]

PIKE_LENGTH = 41


def _bot(ink: str, acc: str, paper: str) -> tuple[str, tuple[int, int]]:
    return (
        f'<line x1="64" y1="38" x2="64" y2="27" stroke="{ink}" stroke-width="3.5" stroke-linecap="round"/>'
        f'<circle cx="64" cy="22" r="4.5" fill="{acc}"/>'
        f'<rect x="38" y="38" width="52" height="46" rx="11" fill="{ink}"/>'
        f'<rect x="90" y="52" width="6" height="16" rx="3" fill="{ink}"/>'
        f'<circle cx="55" cy="58" r="5.5" fill="{acc}"/><circle cx="75" cy="58" r="5.5" fill="{acc}"/>'
        f'<line x1="55" y1="73" x2="75" y2="73" stroke="{paper}" stroke-width="3" stroke-linecap="round"/>',
        (42, 62),
    )


def _rack(ink: str, acc: str, paper: str) -> tuple[str, tuple[int, int]]:
    units = "".join(
        f'<circle cx="51" cy="{y}" r="3" fill="{acc}"/>'
        f'<line x1="61" y1="{y}" x2="80" y2="{y}" stroke="{paper}" stroke-width="3" stroke-linecap="round"/>'
        for y in (30, 52, 74)
    )
    seams = "".join(
        f'<line x1="40" y1="{y}" x2="88" y2="{y}" stroke="{paper}" stroke-width="1.6"/>'
        for y in (41, 63)
    )
    return f'<rect x="40" y="16" width="48" height="72" rx="6" fill="{ink}"/>{seams}{units}', (
        44,
        58,
    )


def _datacenter(ink: str, acc: str, paper: str) -> tuple[str, tuple[int, int]]:
    windows = ""
    for row in range(4):
        for col in range(3):
            fill = acc if (row, col) in ((1, 2), (3, 0)) else paper
            windows += f'<rect x="{46 + col * 15}" y="{30 + row * 14}" width="9" height="8" rx="1.5" fill="{fill}"/>'
    return (
        f'<rect x="38" y="20" width="54" height="68" rx="4" fill="{ink}"/>{windows}'
        f'<rect x="32" y="86" width="66" height="5" rx="2.5" fill="{ink}"/>',
        (42, 58),
    )


def _chip(ink: str, acc: str, paper: str) -> tuple[str, tuple[int, int]]:
    pins = "".join(
        f'<line x1="{x}" y1="20" x2="{x}" y2="28" stroke="{ink}" stroke-width="3" stroke-linecap="round"/>'
        f'<line x1="{x}" y1="72" x2="{x}" y2="80" stroke="{ink}" stroke-width="3" stroke-linecap="round"/>'
        for x in (52, 64, 76)
    ) + "".join(
        f'<line x1="88" y1="{y}" x2="96" y2="{y}" stroke="{ink}" stroke-width="3" stroke-linecap="round"/>'
        for y in (38, 50, 62)
    )
    return (
        f'{pins}<rect x="40" y="26" width="48" height="48" rx="7" fill="{ink}"/>'
        f'<rect x="52" y="38" width="24" height="24" rx="3" fill="{paper}"/>'
        f'<circle cx="64" cy="50" r="4.5" fill="{acc}"/>',
        (44, 52),
    )


def _cyclops(ink: str, acc: str, paper: str) -> tuple[str, tuple[int, int]]:
    return (
        f'<rect x="56" y="76" width="16" height="10" rx="3" fill="{ink}"/>'
        f'<rect x="44" y="84" width="40" height="6" rx="3" fill="{ink}"/>'
        f'<circle cx="64" cy="50" r="28" fill="{ink}"/>'
        f'<circle cx="64" cy="50" r="13" fill="{paper}"/><circle cx="64" cy="50" r="6.5" fill="{acc}"/>',
        (40, 55),
    )


def _promptbot(ink: str, acc: str, paper: str) -> tuple[str, tuple[int, int]]:
    return (
        f'<path d="M48 22 H80 a12 12 0 0 1 12 12 V54 a12 12 0 0 1 -12 12 H66 L52 82 V66 H48 '
        f'a12 12 0 0 1 -12 -12 V34 a12 12 0 0 1 12 -12 Z" fill="{ink}"/>'
        f'<circle cx="52" cy="44" r="4" fill="{acc}"/><circle cx="64" cy="44" r="4" fill="{acc}"/>'
        f'<circle cx="76" cy="44" r="4" fill="{acc}"/>',
        (40, 46),
    )


TARGETS: dict[Target, TargetFn] = {
    "bot": _bot,
    "rack": _rack,
    "datacenter": _datacenter,
    "chip": _chip,
    "cyclops": _cyclops,
    "promptbot": _promptbot,
}

# Bounding box of each target's drawing, used to fit the whole mark into its container.
TARGET_BBOX: dict[Target, BBox] = {
    "bot": (32, 17, 96, 84),
    "rack": (40, 16, 88, 88),
    "datacenter": (32, 20, 98, 91),
    "chip": (40, 20, 96, 80),
    "cyclops": (36, 22, 92, 90),
    "promptbot": (36, 22, 92, 82),
}


def pike(style: PikeStyle, acc: str, paper: str, length: int = PIKE_LENGTH) -> str:
    """A pike in local coordinates: tip at the origin, pointing +x, shaft toward -x."""

    def halo(x1: float, x2: float, width: float) -> str:
        return (
            f'<line x1="{x1}" y1="0" x2="{x2}" y2="0" stroke="{paper}" '
            f'stroke-width="{width}" stroke-linecap="round"/>'
        )

    if style == "needle":
        return (
            halo(-length, -14, 6.5)
            + f'<polygon points="0,0 -28,-3.4 -28,3.4" fill="{acc}" stroke="{paper}" '
            f'stroke-width="2.2" stroke-linejoin="round" paint-order="stroke"/>'
            + f'<line x1="{-length}" y1="0" x2="-20" y2="0" stroke="{acc}" stroke-width="2.6" stroke-linecap="round"/>'
            + f'<circle cx="{-length}" cy="0" r="4" fill="{acc}" stroke="{paper}" stroke-width="1.6" paint-order="stroke"/>'
        )
    tip = (
        f'<polygon points="0,0 -19,-7.5 -19,7.5" fill="{acc}" stroke="{paper}" stroke-width="2.4" '
        f'stroke-linejoin="round" paint-order="stroke"/>'
    )
    shaft = (
        halo(-length, -14, 9)
        + f'<line x1="{-length}" y1="0" x2="-14" y2="0" stroke="{acc}" stroke-width="4.6" stroke-linecap="round"/>'
    )
    if style == "spear":
        return shaft + tip
    if style == "lance":
        guard = f'<line x1="-26" y1="-10" x2="-26" y2="10" stroke="{acc}" stroke-width="3.2" stroke-linecap="round"/>'
        fletch = (
            f'<polygon points="{-length},0 {-length - 9},-6.5 {-length - 5},0 {-length - 9},6.5" fill="{acc}" '
            f'stroke="{paper}" stroke-width="1.6" stroke-linejoin="round" paint-order="stroke"/>'
        )
        return shaft + guard + tip + fletch
    trails = "".join(
        f'<line x1="{-length * 0.92}" y1="{y}" x2="{-length * 0.5}" y2="{y}" stroke="{acc}" '
        f'stroke-width="1.6" stroke-linecap="round" opacity=".65"/>'
        for y in (-8, 8)
    )
    return trails + shaft + tip


def impact(kind: Impact, px: float, py: float, angle: int, paper: str) -> str:
    """Marks where the pike lands: radiating cracks, a dashed ring, or nothing."""
    if kind == "none":
        return ""
    if kind == "ring":
        return (
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="10" fill="none" stroke="{paper}" '
            f'stroke-width="1.6" stroke-dasharray="3 3"/>'
        )
    out = ""
    for spread in (-38, 0, 38):
        a = math.radians(-angle + spread)
        x1, y1 = px + 8 * math.cos(a), py + 8 * math.sin(a)
        x2, y2 = px + 15 * math.cos(a), py + 15 * math.sin(a)
        out += (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{paper}" '
            f'stroke-width="2" stroke-linecap="round"/>'
        )
    return out
