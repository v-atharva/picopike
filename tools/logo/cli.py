"""Command line: ``python -m tools.logo {build,check,concepts}``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.logo.concepts import write_round
from tools.logo.model import BrandSpec, load_spec
from tools.logo.render import render_logo

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "brand" / "logo.spec.json"
ASSETS = ROOT / "assets"
CONCEPTS_DIR = ASSETS / "logo-concepts" / "round-2"


def official_assets(spec: BrandSpec) -> dict[Path, str]:
    """Every built file under ``assets/`` and its exact expected contents."""
    files: dict[Path, str] = {}
    for suffix, palette in (("", spec.light), ("-dark", spec.dark)):
        files[ASSETS / f"logo{suffix}.svg"] = render_logo(
            spec.mark, spec.wordmark, palette, "horizontal", background=False
        )
        files[ASSETS / f"icon{suffix}.svg"] = render_logo(
            spec.mark, spec.wordmark, palette, "icon", background=False
        )
    return files


def cmd_build(_: argparse.Namespace) -> int:
    for path, content in official_assets(load_spec(SPEC_PATH)).items():
        path.write_text(content)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


def cmd_check(_: argparse.Namespace) -> int:
    drifted = [
        path
        for path, content in official_assets(load_spec(SPEC_PATH)).items()
        if not path.exists() or path.read_text() != content
    ]
    for path in drifted:
        print(f"out of date: {path.relative_to(ROOT)}", file=sys.stderr)
    if drifted:
        print("run: python -m tools.logo build", file=sys.stderr)
    return 1 if drifted else 0


def cmd_concepts(_: argparse.Namespace) -> int:
    paths = write_round(CONCEPTS_DIR)
    print(f"wrote {len(paths)} files to {CONCEPTS_DIR.relative_to(ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.logo", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="regenerate assets/ from brand/logo.spec.json").set_defaults(
        func=cmd_build
    )
    sub.add_parser("check", help="fail if assets/ differ from the spec").set_defaults(
        func=cmd_check
    )
    sub.add_parser("concepts", help="regenerate the 50-concept exploration round").set_defaults(
        func=cmd_concepts
    )
    args = parser.parse_args(argv)
    return int(args.func(args))
