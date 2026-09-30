"""Deterministic logo generator: spec in, SVG out.

The chosen design lives in ``brand/logo.spec.json``. Everything under ``assets/`` that is
named ``logo*.svg`` or ``icon*.svg`` is generated from it, so refining the logo means editing
the spec (or the parts) and re-running ``python -m tools.logo build``.
"""

from tools.logo.model import BrandSpec, MarkSpec, Palette, WordmarkSpec, load_spec
from tools.logo.render import render_logo

__all__ = [
    "BrandSpec",
    "MarkSpec",
    "Palette",
    "WordmarkSpec",
    "load_spec",
    "render_logo",
]
