"""The contract every detection lane implements, shared by the router and the benchmark."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any, Protocol, TypedDict, runtime_checkable

ANY_LANGUAGE = "*"


class LaneResult(TypedDict):
    """One lane's verdict on one input, kept verbatim in the trace for replay.

    ``raw`` and ``error`` are written to the trace even when text storage is off, so they must
    never contain the input or excerpts of it.
    """

    lane: str
    score: float | None
    labels: dict[str, float]
    category: str | None
    latency_ms: float
    cost_usd: float
    error: str | None
    raw: dict[str, Any]


@runtime_checkable
class Detector(Protocol):
    """A lane: scores one input for P(unsafe) and never raises for a bad input.

    ``detect`` must not block the event loop; run blocking work such as model inference in a thread.
    """

    name: str
    languages: frozenset[str]

    async def detect(self, text: str, *, lang: str | None) -> LaneResult: ...


class InvalidLaneResult(ValueError):
    """A lane returned a result that would corrupt fusion or the trace."""


def failed(lane: str, error: str, *, latency_ms: float = 0.0) -> LaneResult:
    """The result recorded for a lane that raised or timed out."""
    return LaneResult(
        lane=lane,
        score=None,
        labels={},
        category=None,
        latency_ms=latency_ms,
        cost_usd=0.0,
        error=error,
        raw={},
    )


def skipped(lane: str, reason: str) -> LaneResult:
    """The result recorded for a lane that was deliberately not run.

    Use it for fast mode, a request outside the HOLD band, an exhausted budget or an unsupported
    language. Unlike ``failed`` it is not an error, so it never marks the request as degraded.
    """
    return LaneResult(
        lane=lane,
        score=None,
        labels={},
        category=None,
        latency_ms=0.0,
        cost_usd=0.0,
        error=None,
        raw={"skipped": reason},
    )


def check_lane_result(result: LaneResult) -> LaneResult:
    """Return ``result`` unchanged, or raise ``InvalidLaneResult`` if it is unusable.

    Guarantees the exact key set, field types, finite numbers and a JSON-safe payload, so fusion
    and the trace writer can trust whatever a lane returns.
    """
    if not isinstance(result, Mapping):
        raise InvalidLaneResult(f"a lane result must be a mapping, got {type(result).__name__}")
    _check_keys(result)
    lane = result["lane"]
    if not isinstance(lane, str) or not lane:
        raise InvalidLaneResult(f"lane must be a non-empty string, got {lane!r}")
    category = result["category"]
    if category is not None and not isinstance(category, str):
        raise InvalidLaneResult(f"{lane}: category must be a string or None, got {category!r}")
    labels = _str_keyed(result["labels"], f"{lane}: labels")
    _str_keyed(result["raw"], f"{lane}: raw")
    if result["score"] is not None:
        _check_probability(result["score"], f"{lane}: score")
    for head, probability in labels.items():
        _check_probability(probability, f"{lane}: labels[{head!r}]")
    for key in ("latency_ms", "cost_usd"):
        value = result[key]
        _check_number(value, f"{lane}: {key}")
        if value < 0:
            raise InvalidLaneResult(f"{lane}: {key} must be finite and non-negative, got {value!r}")
    _check_error(lane, result)
    _check_json(lane, result)
    return result


def supports(detector: Detector, lang: str | None) -> bool:
    """Whether ``detector`` should run for ``lang``; unknown language means try every lane."""
    return lang is None or ANY_LANGUAGE in detector.languages or lang in detector.languages


def _check_keys(result: Mapping[str, Any]) -> None:
    missing = sorted(LaneResult.__required_keys__ - result.keys())
    extra = sorted(result.keys() - LaneResult.__required_keys__)
    if missing or extra:
        problems = [f"missing {', '.join(missing)}"] if missing else []
        problems += [f"unexpected {', '.join(map(str, extra))}"] if extra else []
        raise InvalidLaneResult(f"{result.get('lane')!r}: lane result has {'; '.join(problems)}")


def _check_error(lane: str, result: LaneResult) -> None:
    error = result["error"]
    if error is None:
        return
    if not isinstance(error, str) or not error:
        raise InvalidLaneResult(f"{lane}: error must be a non-empty string, got {error!r}")
    if result["score"] is not None:
        raise InvalidLaneResult(f"{lane}: a failed lane cannot carry a score")
    if result["labels"]:
        raise InvalidLaneResult(f"{lane}: a failed lane cannot carry labels")


def _check_json(lane: str, result: LaneResult) -> None:
    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise InvalidLaneResult(f"{lane}: result is not JSON-serialisable: {exc}") from exc


def _str_keyed(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise InvalidLaneResult(f"{where} must be a dict with string keys, got {value!r}")
    return value


def _check_number(value: Any, where: str) -> None:
    # Decimal, Fraction and numpy scalars are refused on purpose: lanes convert to float themselves.
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise InvalidLaneResult(f"{where} must be a finite number, got {value!r}")


def _check_probability(value: Any, where: str) -> None:
    _check_number(value, where)
    if not 0.0 <= value <= 1.0:
        raise InvalidLaneResult(f"{where} must be a probability in [0, 1], got {value!r}")
