from collections.abc import Mapping
from typing import Any, cast

import pytest
from tests.fakes import FakeDetector

from picopike.config import ConfigError, LaneConfig
from picopike.detectors.base import Detector, LaneResult
from picopike.detectors.registry import Registry


def fake_factory(name: str, options: Mapping[str, Any]) -> Detector:
    return FakeDetector(name=name, score=float(options.get("score", 0.5)))


def registry() -> Registry:
    r = Registry()
    r.register("fake", fake_factory)
    return r


def lanes(*configs: LaneConfig) -> dict[str, LaneConfig]:
    return {c.name: c for c in configs}


def test_builds_enabled_lanes_in_config_order() -> None:
    built = registry().build(
        lanes(
            LaneConfig(name="b", kind="fake"),
            LaneConfig(name="off", kind="fake", enabled=False),
            LaneConfig(name="a", kind="fake"),
        )
    )
    assert list(built) == ["b", "a"]
    assert all(built[name].name == name for name in built)


def test_options_reach_the_factory() -> None:
    built = registry().build(lanes(LaneConfig(name="x", kind="fake", options={"score": 0.9})))
    detector = built["x"]
    assert isinstance(detector, FakeDetector)
    assert detector.score == 0.9


def test_no_lanes_builds_nothing() -> None:
    assert registry().build({}) == {}


def test_unknown_kind_lists_the_known_ones() -> None:
    with pytest.raises(ConfigError, match=r"unknown kind 'pikee'.*known: fake"):
        registry().build(lanes(LaneConfig(name="pike", kind="pikee")))


def test_disabled_lane_with_unknown_kind_is_ignored() -> None:
    assert registry().build(lanes(LaneConfig(name="later", kind="judge", enabled=False))) == {}


def test_kind_cannot_be_registered_twice() -> None:
    r = registry()
    with pytest.raises(ValueError, match="already registered"):
        r.register("fake", fake_factory)


def test_kinds_are_sorted() -> None:
    r = registry()
    r.register("alpha", fake_factory)
    assert r.kinds() == ["alpha", "fake"]


def test_factory_must_return_a_detector() -> None:
    r = Registry()
    r.register("broken", lambda name, options: object())
    with pytest.raises(TypeError, match="broken"):
        r.build(lanes(LaneConfig(name="x", kind="broken")))


def test_detector_name_must_match_the_lane() -> None:
    r = Registry()
    r.register("fixed", lambda name, options: FakeDetector(name="other"))
    with pytest.raises(ValueError, match="'other'"):
        r.build(lanes(LaneConfig(name="x", kind="fixed")))


def test_detect_must_be_a_coroutine_function() -> None:
    class BlockingDetector:
        name = "x"
        languages = frozenset({"en"})

        def detect(self, text: str, *, lang: str | None) -> LaneResult:
            raise NotImplementedError

    r = Registry()
    r.register("blocking", lambda name, options: cast(Detector, BlockingDetector()))
    with pytest.raises(TypeError, match=r"blocking.*async"):
        r.build(lanes(LaneConfig(name="x", kind="blocking")))


def test_languages_must_be_a_frozenset() -> None:
    detector = FakeDetector(name="x")
    detector.languages = cast(frozenset[str], "en")
    r = Registry()
    r.register("stringy", lambda name, options: detector)
    with pytest.raises(TypeError, match=r"stringy.*frozenset"):
        r.build(lanes(LaneConfig(name="x", kind="stringy")))
