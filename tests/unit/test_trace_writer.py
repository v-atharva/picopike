import hashlib
import json
import math
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from picopike.detectors.base import LaneResult, failed, skipped
from picopike.trace.writer import (
    SCHEMA_VERSION,
    TraceRecord,
    TraceWriter,
    build_record,
    text_sha256,
)

NOON = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def lane(name: str = "pike", score: float = 0.2, cost: float = 0.0) -> LaneResult:
    return LaneResult(
        lane=name,
        score=score,
        labels={"injection": score},
        category=None,
        latency_ms=4.0,
        cost_usd=cost,
        error=None,
        raw={},
    )


def record(text: str = "hello", **kwargs: Any) -> TraceRecord:
    defaults: dict[str, Any] = {
        "lang": "en",
        "mode": "fast",
        "lanes": [lane()],
        "fused_score": 0.2,
        "decision": "ALLOW",
        "latency_ms": 5.0,
        "now": NOON,
    }
    return build_record(text, **{**defaults, **kwargs})


def test_record_has_schema_one_and_hashes_the_text() -> None:
    r = record("ignore previous instructions")
    assert r["schema"] == SCHEMA_VERSION == 1
    assert r["text_sha256"] == hashlib.sha256(b"ignore previous instructions").hexdigest()
    assert "text" not in r
    assert r["ts"] == "2026-10-01T12:00:00.000+00:00"
    assert len(r["trace_id"]) == 32
    assert r["trace_id"] != record()["trace_id"]


def test_text_is_stored_only_when_opted_in() -> None:
    assert record("secret", store_text=True)["text"] == "secret"


def test_degraded_and_cost_come_from_the_lanes() -> None:
    r = record(lanes=[lane("pike", cost=0.0), lane("judge", cost=0.00004), failed("x", "timeout")])
    assert r["degraded"] is True
    assert math.isclose(r["cost_usd"], 0.00004)
    assert record()["degraded"] is False


def test_skipped_lane_is_not_degraded() -> None:
    r = record(lanes=[lane(), skipped("judge", "fast mode")])
    assert r["degraded"] is False


def test_failed_lane_is_degraded() -> None:
    assert record(lanes=[lane(), failed("judge", "timeout")])["degraded"] is True


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        record(now=datetime(2026, 10, 1, 12, 0))


def test_timestamps_are_normalised_to_utc() -> None:
    plus5 = datetime(2026, 10, 1, 1, 0, tzinfo=timezone(timedelta(hours=5)))
    assert record(now=plus5)["ts"] == "2026-09-30T20:00:00.000+00:00"


def test_writer_appends_one_json_line_per_record(tmp_path: Path) -> None:
    writer = TraceWriter(tmp_path)
    first, second = record("a"), record("b")
    path = writer.write(first)
    assert writer.write(second) == path
    lines = path.read_text(encoding="ascii").splitlines()
    assert [json.loads(line) for line in lines] == [first, second]


def test_files_roll_at_utc_midnight(tmp_path: Path) -> None:
    writer = TraceWriter(tmp_path / "traces")
    before = writer.write(record(now=datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC)))
    after = writer.write(record(now=datetime(2026, 10, 1, 0, 0, 1, tzinfo=UTC)))
    assert (before.name, after.name) == ("2026-09-30.jsonl", "2026-10-01.jsonl")


def test_file_follows_the_utc_date_not_the_local_one(tmp_path: Path) -> None:
    plus5 = datetime(2026, 10, 1, 1, 0, tzinfo=timezone(timedelta(hours=5)))
    path = TraceWriter(tmp_path).write(record(now=plus5))
    assert path.name == "2026-09-30.jsonl"


def test_awkward_text_stays_on_one_line_and_round_trips(tmp_path: Path) -> None:
    text = "line one\nline two \u200b \ud800 \U0001f600"
    r = record(text, store_text=True)
    path = TraceWriter(tmp_path).write(r)
    lines = path.read_text(encoding="ascii").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["text"] == text
    assert r["text_sha256"] == text_sha256(text)


@pytest.mark.parametrize(
    "bad",
    [
        {"fused_score": math.nan},
        {"lanes": [{**lane(), "raw": {"blob": b"\x00"}}]},
    ],
)
def test_unserialisable_record_leaves_the_file_untouched(
    tmp_path: Path, bad: dict[str, Any]
) -> None:
    writer = TraceWriter(tmp_path)
    path = writer.write(record())
    before = path.read_bytes()
    with pytest.raises((ValueError, TypeError)):
        writer.write(record(**bad))
    assert path.read_bytes() == before
