"""The lane kinds PicoPike ships with, keyed by the ``kind`` used in ``picopike.toml``."""

from __future__ import annotations

from picopike.detectors.hard_guard import build_hard_guard
from picopike.detectors.registry import Registry


def builtin_registry() -> Registry:
    registry = Registry()
    registry.register("hard_guard", build_hard_guard)
    return registry
