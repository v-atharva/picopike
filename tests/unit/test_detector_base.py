import asyncio
import math
from decimal import Decimal
from fractions import Fraction
from typing import Any, cast

import pytest
from tests.fakes import FakeDetector

from picopike.detectors.base import (
    ANY_LANGUAGE,
    Detector,
    InvalidLaneResult,
    LaneResult,
    check_lane_result,
    failed,
    skipped,
    supports,
)

_VALID: dict[str, Any] = {
    "lane": "fake",
    "score": 0.5,
    "labels": {"injection": 0.5},
    "category": None,
    "latency_ms": 1.0,
    "cost_usd": 0.0,
    "error": None,
    "raw": {},
}


def result(**overrides: Any) -> LaneResult:
    return cast(LaneResult, {**_VALID, **overrides})


def test_valid_result_is_returned_unchanged() -> None:
    r = result()
    assert check_lane_result(r) is r


def test_missing_score_is_allowed() -> None:
    assert check_lane_result(result(score=None))["score"] is None


@pytest.mark.parametrize("score", [-0.01, 1.01, math.nan, math.inf, -math.inf, True])
def test_unusable_scores_are_rejected(score: object) -> None:
    with pytest.raises(InvalidLaneResult, match="score"):
        check_lane_result(result(score=score))


def test_unusable_label_probability_is_rejected() -> None:
    with pytest.raises(InvalidLaneResult, match="labels\\['jailbreak'\\]"):
        check_lane_result(result(labels={"injection": 0.2, "jailbreak": math.nan}))


@pytest.mark.parametrize("field", ["latency_ms", "cost_usd"])
@pytest.mark.parametrize("value", [-1.0, math.nan, math.inf])
def test_unusable_measurements_are_rejected(field: str, value: float) -> None:
    with pytest.raises(InvalidLaneResult, match=field):
        check_lane_result(result(**{field: value}))


def test_failed_lane_cannot_carry_a_score() -> None:
    with pytest.raises(InvalidLaneResult, match="failed lane"):
        check_lane_result(result(error="timeout", score=0.9))


def test_failed_builds_a_valid_empty_result() -> None:
    r = check_lane_result(failed("pike", "timeout after 200 ms", latency_ms=200.0))
    assert r["lane"] == "pike"
    assert r["score"] is None
    assert r["error"] == "timeout after 200 ms"
    assert r["latency_ms"] == 200.0
    assert r["cost_usd"] == 0.0


def test_failed_lane_needs_a_message() -> None:
    with pytest.raises(InvalidLaneResult, match="error"):
        check_lane_result(result(error="", score=None, labels={}))


def test_failed_lane_cannot_carry_labels() -> None:
    with pytest.raises(InvalidLaneResult, match="labels"):
        check_lane_result(result(error="timeout", score=None, labels={"injection": 0.5}))


def test_skipped_builds_a_valid_result_that_is_not_an_error() -> None:
    r = check_lane_result(skipped("judge", "fast mode"))
    assert r["lane"] == "judge"
    assert r["score"] is None
    assert r["labels"] == {}
    assert r["error"] is None
    assert r["latency_ms"] == 0.0
    assert r["cost_usd"] == 0.0
    assert r["raw"] == {"skipped": "fast mode"}


def test_missing_key_is_rejected_by_name() -> None:
    partial = {k: v for k, v in _VALID.items() if k != "category"}
    with pytest.raises(InvalidLaneResult, match="category"):
        check_lane_result(cast(LaneResult, partial))


def test_extra_key_is_rejected_by_name() -> None:
    with pytest.raises(InvalidLaneResult, match="verdict"):
        check_lane_result(cast(LaneResult, {**_VALID, "verdict": "unsafe"}))


def test_non_mapping_is_rejected() -> None:
    with pytest.raises(InvalidLaneResult, match="mapping"):
        check_lane_result(cast(LaneResult, [1, 2]))


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"score": Decimal("0.5")}, "score"),
        ({"score": "0.5"}, "score"),
        ({"labels": {"injection": Fraction(1, 2)}}, "labels"),
        ({"labels": None}, "labels"),
        ({"labels": {1: 0.5}}, "labels"),
        ({"raw": None}, "raw"),
        ({"raw": {1: "x"}}, "raw"),
        ({"lane": ""}, "lane"),
        ({"lane": 3}, "lane"),
        ({"category": 3}, "category"),
        ({"latency_ms": "1"}, "latency_ms"),
        ({"error": 3, "score": None, "labels": {}}, "error"),
    ],
)
def test_wrong_types_raise_invalid_lane_result(overrides: dict[str, Any], match: str) -> None:
    with pytest.raises(InvalidLaneResult, match=match):
        check_lane_result(result(**overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"latency_ms": True},
        {"cost_usd": True},
        {"labels": {"injection": True}},
    ],
)
def test_bool_is_not_a_number(overrides: dict[str, Any]) -> None:
    with pytest.raises(InvalidLaneResult):
        check_lane_result(result(**overrides))


def test_raw_must_be_json_serialisable() -> None:
    with pytest.raises(InvalidLaneResult, match=r"fake.*JSON"):
        check_lane_result(result(raw={"blob": b"x"}))


def test_raw_cannot_hold_nan() -> None:
    with pytest.raises(InvalidLaneResult, match="JSON"):
        check_lane_result(result(raw={"x": math.nan}))


def test_fake_detector_satisfies_the_protocol() -> None:
    detector = FakeDetector()
    assert isinstance(detector, Detector)
    r = asyncio.run(detector.detect("hello", lang="en"))
    assert check_lane_result(r)["lane"] == "fake"


def test_object_without_detect_is_not_a_detector() -> None:
    class NotADetector:
        name = "x"
        languages = frozenset({"en"})

    assert not isinstance(NotADetector(), Detector)


def test_supports_checks_declared_languages() -> None:
    english = FakeDetector(languages=frozenset({"en"}))
    anything = FakeDetector(languages=frozenset({ANY_LANGUAGE}))
    assert supports(english, "en")
    assert not supports(english, "ru")
    assert supports(english, None)
    assert supports(anything, "ru")
