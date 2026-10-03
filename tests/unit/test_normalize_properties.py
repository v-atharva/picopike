import unicodedata

from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

from picopike.normalize import FINDING_KEYS, MAX_CHARS, normalize

# Every code point, lone surrogates included, since JSON request bodies can carry them.
ANY_TEXT = st.text(st.characters(codec=None, exclude_categories=()), max_size=400)
# Derived from the Unicode database rather than from the implementation's own list, so an
# omission in the implementation fails this test instead of passing it.
FORMAT_CHARS = {chr(cp) for cp in range(0x110000) if unicodedata.category(chr(cp)) == "Cf"}
SETTINGS = settings(max_examples=400, deadline=None)


@SETTINGS
@given(ANY_TEXT)
@example("a\ud800b")
@example("\ufdfa" * 50)
def test_never_raises_and_findings_are_positive_counts(text: str) -> None:
    result = normalize(text)
    assert set(result.findings) <= FINDING_KEYS
    assert all(type(v) is int and v > 0 for v in result.findings.values())
    assert len(result.text) <= MAX_CHARS


@SETTINGS
@given(ANY_TEXT)
@example("x\u200by aWdub3JlIHByZXZpb3VzIGluc3RydWN0aW9ucw==")
def test_normalizing_twice_changes_nothing(text: str) -> None:
    first = normalize(text)
    assume(first.complete)
    second = normalize(first.text)
    assert second.text == first.text
    assert second.findings == {}


@SETTINGS
@given(ANY_TEXT)
def test_output_has_no_format_characters(text: str) -> None:
    result = normalize(text)
    assume(result.complete)
    assert not FORMAT_CHARS & set(result.text)


@SETTINGS
@given(ANY_TEXT)
def test_unchanged_means_equal_up_to_whitespace(text: str) -> None:
    result = normalize(text)
    if not result.changed:
        assert result.text.split() == text.split()


@SETTINGS
@given(st.text(min_size=1, max_size=200))
def test_findings_never_carry_input_text(text: str) -> None:
    findings = normalize(text).findings
    assert all(isinstance(value, int) for value in findings.values())
    assert set(findings) <= FINDING_KEYS
