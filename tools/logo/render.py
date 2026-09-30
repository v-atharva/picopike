"""Compose parts into a finished mark, wordmark and full lockup."""

# ruff: noqa: E501  (SVG markup is clearer unbroken)

from __future__ import annotations

import math

from tools.logo.model import Container, Layout, MarkSpec, Palette, WordmarkSpec, WordmarkStyle
from tools.logo.parts import (
    PIKE_LENGTH,
    TARGET_BBOX,
    TARGETS,
    BBox,
    impact,
    pike,
)
from tools.logo.typeset import BOLD, REGULAR, measure, set_text

MARK_BOX = 130  # the square the mark (and icon) is drawn in
SHIELD_PATH = "M65 5 L113 19 V66 C113 97 91 117 65 125 C39 117 17 97 17 66 V19 Z"

SANS = "Inter, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"

# Outlined caps wordmark: sizes per layout, and tracking in canvas units.
CAPS_SIZE: dict[Layout, int] = {"horizontal": 38, "stacked": 32}
CAPS_TRACKING = 1.0
WORDMARK_X = 140
WORDMARK_BASELINE = 78

SOCIAL_SIZE = (1280, 640)

# layout -> (width, height)
CANVAS: dict[Layout, tuple[int, int]] = {
    "icon": (130, 130),
    "stacked": (260, 210),
    "horizontal": (480, 130),
}


def _container(kind: Container, tint: str) -> tuple[str, tuple[int, int, int]]:
    """Container SVG plus the (fit box, centre x, centre y) the mark is fitted into."""
    if kind == "circle":
        return f'<circle cx="65" cy="65" r="62" fill="{tint}"/>', (80, 65, 65)
    if kind == "square":
        return f'<rect x="3" y="3" width="124" height="124" rx="30" fill="{tint}"/>', (88, 65, 65)
    if kind == "shield":
        return f'<path d="{SHIELD_PATH}" fill="{tint}"/>', (72, 65, 59)
    return "", (114, 65, 65)


def _mark_group(mark: MarkSpec, pal: Palette, paper: str) -> tuple[str, BBox]:
    """The target, impact and pike (flipped if asked) and their combined bounding box."""
    target_svg, (px, py) = TARGETS[mark.target](pal.ink, pal.accent, paper)
    body = (
        target_svg
        + impact(mark.impact, px, py, mark.angle, paper)
        + f'<g transform="translate({px} {py}) rotate({-mark.angle})">'
        f"{pike(mark.pike, pal.accent, paper)}</g>"
    )
    x0, y0, x1, y1 = TARGET_BBOX[mark.target]
    theta = math.radians(mark.angle)
    tail_x = px - (PIKE_LENGTH + 10) * math.cos(theta)
    tail_y = py + (PIKE_LENGTH + 10) * math.sin(theta)
    x0, y1 = min(x0, tail_x - 4), max(y1, tail_y + 4)
    if mark.flip:
        body = f'<g transform="translate({MARK_BOX} 0) scale(-1 1)">{body}</g>'
        x0, x1 = MARK_BOX - x1, MARK_BOX - x0
    return body, (x0, y0, x1, y1)


def render_mark(mark: MarkSpec, pal: Palette) -> str:
    """The container plus the mark, auto-fitted and centred in a 130x130 box."""
    container_svg, (box, cx, cy) = _container(mark.container, pal.tint)
    paper = pal.tint if mark.container != "none" else pal.bg
    body, (x0, y0, x1, y1) = _mark_group(mark, pal, paper)
    scale = box / max(x1 - x0, y1 - y0)
    tx, ty = cx - scale * (x0 + x1) / 2, cy - scale * (y0 + y1) / 2
    return (
        f'{container_svg}<g transform="translate({tx:.1f} {ty:.1f}) scale({scale:.3f})">{body}</g>'
    )


def _outlined_caps(pal: Palette, layout: Layout) -> str:
    size = CAPS_SIZE[layout]
    if layout == "stacked":
        width = measure(BOLD, "PICOPIKE", size=size, letter_spacing=CAPS_TRACKING)
        x, baseline = 130 - width / 2, 192.0
    else:
        x, baseline = WORDMARK_X, WORDMARK_BASELINE
    first = set_text(
        BOLD, "PICO", size=size, x=x, baseline=baseline, fill=pal.ink, letter_spacing=CAPS_TRACKING
    )
    second = set_text(
        BOLD,
        "PIKE",
        size=size,
        x=first.end_x,
        baseline=baseline,
        fill=pal.accent,
        letter_spacing=CAPS_TRACKING,
    )
    return first.svg + second.svg


def render_wordmark(
    style: WordmarkStyle, pal: Palette, layout: Layout, *, outline: bool = False
) -> str:
    """The name as live text, or as vector outlines for the bundled ``caps`` style."""
    if outline:
        if style != "caps":
            raise ValueError(f"outlines are only bundled for the 'caps' wordmark, not {style!r}")
        return _outlined_caps(pal, layout)
    ink, acc = pal.ink, pal.accent
    stacked = layout == "stacked"
    x, y, anchor = (130, 192, "middle") if stacked else (140, 78, "start")
    pos = f'x="{x}" y="{y}" text-anchor="{anchor}"'
    if style == "light-bold":
        size = 42 if stacked else 46
        return (
            f'<text {pos} font-family="{SANS}" font-size="{size}" letter-spacing="-1" fill="{ink}">'
            f'<tspan font-weight="300">Pico</tspan><tspan font-weight="800">Pike</tspan></text>'
        )
    if style == "caps":
        size = 32 if stacked else 38
        return (
            f'<text {pos} font-family="{SANS}" font-size="{size}" font-weight="700" letter-spacing="1" '
            f'fill="{ink}">PICO<tspan fill="{acc}">PIKE</tspan></text>'
        )
    if style == "mono":
        size = 34 if stacked else 40
        return (
            f'<text {pos} font-family="{MONO}" font-size="{size}" fill="{acc}">pico'
            f'<tspan font-weight="700" fill="{ink}">pike</tspan></text>'
        )
    size = 38 if stacked else 44
    return (
        f'<text {pos} font-family="{SANS}" font-size="{size}" letter-spacing="-0.5" fill="{ink}">'
        f'<tspan font-weight="300">pico</tspan><tspan font-weight="800" fill="{acc}">/</tspan>'
        f'<tspan font-weight="800">pike</tspan></text>'
    )


def render_logo(
    mark: MarkSpec,
    wordmark: WordmarkSpec,
    pal: Palette,
    layout: Layout,
    *,
    background: bool,
    outline: bool = False,
) -> str:
    """A complete, standalone SVG document. ``background=False`` leaves the canvas transparent."""
    width, height = CANVAS[layout]
    mark_svg = render_mark(mark, pal)
    if layout == "icon":
        body = mark_svg
    else:
        text = render_wordmark(wordmark.style, pal, layout, outline=outline)
        if layout == "stacked":
            body = f'<g transform="translate(65 4)">{mark_svg}</g>{text}'
        else:
            body = mark_svg + text
    backdrop = (
        f'\n  <rect width="{width}" height="{height}" fill="{pal.bg}"/>' if background else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="PicoPike">{backdrop}\n  {body}\n</svg>\n'
    )


def render_social_card(mark: MarkSpec, pal: Palette, tagline: str) -> str:
    """A 1280x640 repository preview: the outlined lockup above a one-line tagline."""
    width, height = SOCIAL_SIZE
    # The lockup's visible content spans from the badge edge to the end of the wordmark.
    left = 3
    right = WORDMARK_X + measure(
        BOLD, "PICOPIKE", size=CAPS_SIZE["horizontal"], letter_spacing=CAPS_TRACKING
    )
    scale = 2.2
    tx = width / 2 - scale * (left + right) / 2
    ty = 250 - scale * 65
    lockup = render_mark(mark, pal) + _outlined_caps(pal, "horizontal")
    tag_size = 34
    tag_x = width / 2 - measure(REGULAR, tagline, size=tag_size) / 2
    tag = set_text(REGULAR, tagline, size=tag_size, x=tag_x, baseline=500, fill=pal.ink)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" aria-label="PicoPike">\n'
        f'  <rect width="{width}" height="{height}" fill="{pal.bg}"/>\n'
        f'  <g transform="translate({tx:.1f} {ty:.1f}) scale({scale})">{lockup}</g>\n'
        f'  <g opacity="0.72">{tag.svg}</g>\n</svg>\n'
    )
