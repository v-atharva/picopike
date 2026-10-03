"""The hard guard: a deterministic lane that a prompt cannot argue out of its findings."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

from picopike.config import ConfigError
from picopike.detectors.base import ANY_LANGUAGE, LaneResult
from picopike.detectors.rules import match_rules, top_severity
from picopike.inputs import Prepared, cheap_to_match, cheap_to_prepare, prepare
from picopike.workers import run_cpu


class HardGuard:
    """Reports rule matches and a never-ALLOW floor; it does not forecast a probability.

    ``score`` is always None, because a rule match is evidence, not P(unsafe). Matches are labels
    for fusion, and ``raw.floor`` is a policy constraint the router enforces. The lane never
    decides HOLD or BLOCK on its own.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.languages = frozenset({ANY_LANGUAGE})

    async def detect(self, text: str, *, lang: str | None) -> LaneResult:
        """Prepare and match ``text``; latency includes the preparation."""
        start = time.perf_counter()
        if cheap_to_prepare(text):
            return self._prepare_and_match(text, lang, start)
        return await run_cpu(self._prepare_and_match, text, lang, start)

    async def detect_prepared(self, prepared: Prepared) -> LaneResult:
        """Match an already prepared request; latency excludes the preparation."""
        start = time.perf_counter()
        if cheap_to_match(prepared):
            return self._result(prepared, start)
        return await run_cpu(self._result, prepared, start)

    def _prepare_and_match(self, text: str, lang: str | None, start: float) -> LaneResult:
        return self._result(prepare(text, lang=lang), start)

    def _result(self, prepared: Prepared, start: float) -> LaneResult:
        matches = match_rules(prepared)
        severity = top_severity(matches)
        return LaneResult(
            lane=self.name,
            score=None,
            labels={f"rule:{m.id}": 1.0 for m in matches},
            category=None,
            latency_ms=(time.perf_counter() - start) * 1000,
            cost_usd=0.0,
            error=None,
            raw={
                "rules": [m.id for m in matches],
                "severity": severity,
                "floor": "HOLD" if severity == "high" else None,
                "complete": prepared.normalized.complete,
                "findings": dict(prepared.normalized.findings),
            },
        )


def build_hard_guard(name: str, options: Mapping[str, Any]) -> HardGuard:
    if options:
        raise ConfigError(
            f"lane {name!r}: hard_guard takes no options, got {', '.join(sorted(options))}"
        )
    return HardGuard(name)
