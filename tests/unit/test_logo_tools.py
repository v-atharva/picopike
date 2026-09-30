"""Guards for the brand pipeline: the spec, the generator and the committed assets must agree."""

import xml.etree.ElementTree as ET

import pytest

from tools.logo.cli import SPEC_PATH, cmd_check, official_assets
from tools.logo.concepts import COUNT, PALETTES, plan, render_concept
from tools.logo.model import load_spec
from tools.logo.render import CANVAS, render_logo, render_social_card, render_wordmark
from tools.logo.typeset import BOLD, measure, set_text


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


def test_official_lockups_are_outlined() -> None:
    for path, content in official_assets(load_spec(SPEC_PATH)).items():
        assert "<text" not in content, f"{path.name} still depends on an installed font"


def test_outlines_are_only_bundled_for_caps() -> None:
    spec = load_spec(SPEC_PATH)
    with pytest.raises(ValueError, match="caps"):
        render_wordmark("mono", spec.light, "horizontal", outline=True)


def test_measure_matches_the_typeset_run() -> None:
    size, tracking = 38, 1.0
    run = set_text(
        BOLD, "PICOPIKE", size=size, x=0, baseline=0, fill="#000", letter_spacing=tracking
    )
    # The run's pen position includes tracking after the last glyph; measure excludes it.
    assert run.end_x == pytest.approx(
        measure(BOLD, "PICOPIKE", size=size, letter_spacing=tracking) + tracking
    )


def test_social_card_is_repository_preview_size() -> None:
    spec = load_spec(SPEC_PATH)
    root = ET.fromstring(render_social_card(spec.mark, spec.dark, spec.tagline))
    assert root.attrib["viewBox"] == "0 0 1280 640"
