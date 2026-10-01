"""Build lanes from configuration, so a benchmark row and a serving lane are the same object."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any

from picopike.config import ConfigError, LaneConfig
from picopike.detectors.base import Detector

DetectorFactory = Callable[[str, Mapping[str, Any]], Detector]


class Registry:
    """Maps a lane ``kind`` to the factory that builds it."""

    def __init__(self) -> None:
        self._factories: dict[str, DetectorFactory] = {}

    def register(self, kind: str, factory: DetectorFactory) -> None:
        if kind in self._factories:
            raise ValueError(f"detector kind already registered: {kind!r}")
        self._factories[kind] = factory

    def kinds(self) -> list[str]:
        return sorted(self._factories)

    def build(self, lanes: Mapping[str, LaneConfig]) -> dict[str, Detector]:
        """Instantiate every enabled lane, keeping configuration order."""
        detectors: dict[str, Detector] = {}
        for lane in lanes.values():
            if not lane.enabled:
                continue
            factory = self._factories.get(lane.kind)
            if factory is None:
                known = ", ".join(self.kinds()) or "none"
                raise ConfigError(
                    f"lane {lane.name!r}: unknown kind {lane.kind!r} (known: {known})"
                )
            detector = factory(lane.name, lane.options)
            if not isinstance(detector, Detector):
                raise TypeError(f"factory for kind {lane.kind!r} did not return a Detector")
            if not inspect.iscoroutinefunction(detector.detect):
                raise TypeError(f"factory for kind {lane.kind!r}: `detect` must be an async def")
            if not isinstance(detector.languages, frozenset):
                raise TypeError(
                    f"factory for kind {lane.kind!r}: `languages` must be a frozenset, "
                    f"got {type(detector.languages).__name__}"
                )
            if detector.name != lane.name:
                raise ValueError(
                    f"lane {lane.name!r}: factory returned a detector named {detector.name!r}"
                )
            detectors[lane.name] = detector
        return detectors
