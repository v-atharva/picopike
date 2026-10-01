"""Load ``picopike.toml``: which lanes run and where traces go."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("picopike.toml")
DEFAULT_TRACE_DIR = Path("evals/traces")

# Unknown keys are rejected so a typo cannot silently fall back to a default.
_TOP_LEVEL_KEYS = frozenset({"lanes", "trace"})
_TRACE_KEYS = frozenset({"dir", "store_text"})
_LANE_KEYS = frozenset({"kind", "enabled"})


class ConfigError(ValueError):
    """The configuration is missing, malformed or names an unknown setting."""


@dataclass(frozen=True)
class LaneConfig:
    """One ``[lanes.<name>]`` table; keys other than ``kind`` and ``enabled`` are options."""

    name: str
    kind: str
    enabled: bool = True
    options: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TraceConfig:
    dir: Path
    store_text: bool = False


@dataclass(frozen=True)
class Config:
    lanes: Mapping[str, LaneConfig]
    trace: TraceConfig


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    """Read and validate a configuration file; relative paths resolve against its folder."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return parse_config(raw, base_dir=path.parent)


def parse_config(raw: Mapping[str, Any], *, base_dir: Path) -> Config:
    _reject_unknown(raw, _TOP_LEVEL_KEYS, "top level")
    lanes = _table(raw.get("lanes", {}), "[lanes]")
    return Config(
        lanes={name: _parse_lane(name, table) for name, table in lanes.items()},
        trace=_parse_trace(_table(raw.get("trace", {}), "[trace]"), base_dir),
    )


def _parse_lane(name: str, value: Any) -> LaneConfig:
    table = _table(value, f"[lanes.{name}]")
    kind = table.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ConfigError(f"[lanes.{name}]: `kind` must be a non-empty string")
    enabled = table.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigError(f"[lanes.{name}]: `enabled` must be true or false")
    options = {key: v for key, v in table.items() if key not in _LANE_KEYS}
    return LaneConfig(name=name, kind=kind, enabled=enabled, options=options)


def _parse_trace(table: Mapping[str, Any], base_dir: Path) -> TraceConfig:
    _reject_unknown(table, _TRACE_KEYS, "[trace]")
    directory = table.get("dir", str(DEFAULT_TRACE_DIR))
    if not isinstance(directory, str) or not directory:
        raise ConfigError("[trace]: `dir` must be a non-empty string")
    store_text = table.get("store_text", False)
    if not isinstance(store_text, bool):
        raise ConfigError("[trace]: `store_text` must be true or false")
    return TraceConfig(dir=base_dir / directory, store_text=store_text)


def _table(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{where} must be a table")
    return value


def _reject_unknown(table: Mapping[str, Any], known: frozenset[str], where: str) -> None:
    unknown = sorted(set(table) - known)
    if unknown:
        raise ConfigError(f"{where}: unknown setting(s) {', '.join(unknown)}")
