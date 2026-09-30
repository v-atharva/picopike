"""Guards for the brand pipeline: the spec, the generator and the committed assets must agree."""

import xml.etree.ElementTree as ET

import pytest
from tools.logo.cli import SPEC_PATH, cmd_check, official_assets
from tools.logo.concepts import COUNT, PALETTES, plan, render_concept
from tools.logo.model import load_spec
from tools.logo.render import CANVAS, render_logo


def test_committed_assets_match_the_spec() -> None:
    drifted = [
        p.name
        for p, content in official_assets(load_spec(SPEC_PATH)).items()
        if p.read_text() != content
    ]
    assert not drifted, f"run `python -m tools.logo build`: {drifted}"


def test_check_command_passes() -> None:
    assert cmd_check(None) == 0  # type: ignore[arg-type]


def test_spec_is_the_chosen_concept() -> None:
    spec = load_spec(SPEC_PATH)
    concept = plan()[spec.concept - 1]
    assert concept.mark == spec.mark
    assert concept.wordmark == spec.wordmark
    assert PALETTES[concept.palette_name] == spec.light


def test_concept_round_is_frozen() -> None:
    concepts = plan()
    assert len(concepts) == COUNT
    assert len({c.filename for c in concepts}) == COUNT
    assert concepts[15].filename == "16-chip-spear-navy-amber-square-horizontal.svg"


@pytest.mark.parametrize("concept", plan(), ids=lambda c: f"{c.number:02d}")
def test_every_concept_is_valid_svg(concept) -> None:  # type: ignore[no-untyped-def]
    root = ET.fromstring(render_concept(concept))
    assert root.tag.endswith("svg")


@pytest.mark.parametrize("layout", list(CANVAS))
def test_official_logo_is_transparent_and_sized(layout) -> None:  # type: ignore[no-untyped-def]
    spec = load_spec(SPEC_PATH)
    svg = render_logo(spec.mark, spec.wordmark, spec.light, layout, background=False)
    root = ET.fromstring(svg)
    width, height = CANVAS[layout]
    assert root.attrib["viewBox"] == f"0 0 {width} {height}"
    assert spec.light.bg not in svg.split("<g", 1)[0]  # no backdrop rect before the artwork
