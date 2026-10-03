import re
from pathlib import Path

import pytest

from picopike.config import ConfigError, load_config, parse_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repository_config_loads_with_hash_only_traces() -> None:
    config = load_config(REPO_ROOT / "picopike.toml")
    assert list(config.lanes) == ["hard_guard"]
    assert config.lanes["hard_guard"].kind == "hard_guard"
    assert config.lanes["hard_guard"].options == {}
    assert config.trace.store_text is False
    assert config.trace.dir == REPO_ROOT / "evals" / "traces"


def test_lanes_keep_order_and_collect_options() -> None:
    config = parse_config(
        {
            "lanes": {
                "pike": {"kind": "pike", "max_tokens": 256},
                "judge": {"kind": "judge", "enabled": False, "model": "m"},
            }
        },
        base_dir=Path("/cfg"),
    )
    assert list(config.lanes) == ["pike", "judge"]
    pike = config.lanes["pike"]
    assert (pike.name, pike.kind, pike.enabled) == ("pike", "pike", True)
    assert pike.options == {"max_tokens": 256}
    assert config.lanes["judge"].enabled is False
    assert config.lanes["judge"].options == {"model": "m"}


def test_relative_trace_dir_is_resolved_against_the_config_file() -> None:
    config = parse_config({"trace": {"dir": "out/traces"}}, base_dir=Path("/cfg"))
    assert config.trace.dir == Path("/cfg/out/traces")


def test_absolute_trace_dir_is_kept() -> None:
    config = parse_config({"trace": {"dir": "/var/traces"}}, base_dir=Path("/cfg"))
    assert config.trace.dir == Path("/var/traces")


def test_defaults_when_sections_are_missing() -> None:
    config = parse_config({}, base_dir=Path("/cfg"))
    assert config.lanes == {}
    assert config.trace.dir == Path("/cfg/evals/traces")
    assert config.trace.store_text is False


def test_missing_file_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "picopike.toml")


def test_directory_in_place_of_the_file_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=re.escape(str(tmp_path))):
        load_config(tmp_path)


def test_file_that_is_not_utf8_is_a_config_error(tmp_path: Path) -> None:
    path = tmp_path / "picopike.toml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ConfigError, match=r"picopike\.toml"):
        load_config(path)


def test_malformed_toml_names_the_file(tmp_path: Path) -> None:
    path = tmp_path / "picopike.toml"
    path.write_text("[trace\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=r"picopike\.toml"):
        load_config(path)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"trcae": {}}, "trcae"),
        ({"trace": {"store_txt": True}}, "store_txt"),
        ({"trace": {"store_text": "false"}}, "store_text"),
        ({"trace": {"dir": 3}}, "dir"),
        ({"trace": {"dir": ""}}, "dir"),
        ({"trace": []}, "trace"),
        ({"lanes": ["pike"]}, "lanes"),
        ({"lanes": {"pike": {}}}, "pike"),
        ({"lanes": {"pike": {"kind": ""}}}, "pike"),
        ({"lanes": {"pike": {"kind": "pike", "enabled": "yes"}}}, "enabled"),
        ({"lanes": {"pike": "pike"}}, "pike"),
    ],
)
def test_invalid_settings_fail_loudly(raw: dict[str, object], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_config(raw, base_dir=Path("/cfg"))
