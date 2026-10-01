"""Append-only JSONL trace: one line per request, and the only input phase 2 reads."""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import NotRequired, TypedDict

from picopike.detectors.base import LaneResult
from picopike.schema import Decision, Mode

SCHEMA_VERSION = 1


class TraceRecord(TypedDict):
    schema: int
    trace_id: str
    ts: str
    text_sha256: str
    text: NotRequired[str]
    lang: str | None
    mode: Mode
    lanes: list[LaneResult]
    fused_score: float | None
    decision: Decision
    degraded: bool
    latency_ms: float
    cost_usd: float


def text_sha256(text: str) -> str:
    # JSON request bodies can carry lone surrogates, which strict UTF-8 refuses to encode.
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def build_record(
    text: str,
    *,
    lang: str | None,
    mode: Mode,
    lanes: Sequence[LaneResult],
    fused_score: float | None,
    decision: Decision,
    latency_ms: float,
    store_text: bool = False,
    now: datetime | None = None,
    trace_id: str | None = None,
) -> TraceRecord:
    """Assemble one request's record; the text itself is kept only when opted in."""
    if now is not None and now.tzinfo is None:
        # A naive value would be read as local time and could land in the wrong day's file.
        raise ValueError("`now` must be timezone-aware")
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    record = TraceRecord(
        schema=SCHEMA_VERSION,
        trace_id=trace_id or uuid.uuid4().hex,
        ts=moment.isoformat(timespec="milliseconds"),
        text_sha256=text_sha256(text),
        lang=lang,
        mode=mode,
        lanes=list(lanes),
        fused_score=fused_score,
        decision=decision,
        degraded=any(result["error"] is not None for result in lanes),
        latency_ms=latency_ms,
        cost_usd=math.fsum(result["cost_usd"] for result in lanes),
    )
    if store_text:
        record["text"] = text
    return record


class TraceWriter:
    """Appends records to ``<directory>/<UTC date>.jsonl``, one file per day."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def path_for(self, record: TraceRecord) -> Path:
        return self._directory / f"{record['ts'][:10]}.jsonl"

    def write(self, record: TraceRecord) -> Path:
        # Serialise before opening the file so a bad record never leaves a partial line.
        # ASCII escapes keep lone surrogates and control characters on a single line.
        line = json.dumps(record, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        path = self.path_for(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="ascii") as handle:
            handle.write(line + "\n")
        return path
