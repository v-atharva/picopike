"""Hard-guard rules: what each one matches and how far it is trusted.

A ``high`` match sets a floor: the request can never be cleared as ALLOW, but fusion still decides
between HOLD and BLOCK, because quoting a forgery (in a tutorial, a bug report) is not the same as
committing one. ``medium`` and ``low`` matches are only features for fusion to weigh.

Rules cover the patterns listed here, not every possible forgery; their matches are evidence, and
none of them is a probability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from picopike.inputs import Prepared
from picopike.normalize import INCOMPLETE_KEYS, MAX_INPUT_CHARS

Severity = Literal["high", "medium", "low"]
_SEVERITY_ORDER: dict[Severity, int] = {"high": 0, "medium": 1, "low": 2}
_ROLE = r"(?:system|assistant|developer)"
_EOL = r"[ \t]*(?:\r\n?|\n|\Z)"
# Word edges that also treat "_" as a separator, so "x_ignore_y" cannot hide a phrase.
_START = r"(?<![^\W_])"
_END = r"(?![^\W_])"


@dataclass(frozen=True)
class TextRule:
    id: str
    severity: Severity
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class FindingRule:
    """Fires when the normalizer's counts for ``keys`` add up to at least ``threshold``.

    Thresholds are absolute counts, not densities: there is no denominator.
    """

    id: str
    severity: Severity
    keys: tuple[str, ...]
    threshold: int


@dataclass(frozen=True)
class Match:
    id: str
    severity: Severity


def _rule(rule_id: str, severity: Severity, pattern: str) -> TextRule:
    return TextRule(rule_id, severity, re.compile(pattern, re.IGNORECASE | re.MULTILINE))


# Bounded gaps ({0,40}) keep every pattern linear in the input length.
TEXT_RULES: tuple[TextRule, ...] = (
    _rule(
        "chat_template_role",
        "high",
        rf"<\|im_start\|>[ \t]*{_ROLE}{_EOL}"
        rf"|<\|start_header_id\|>\s*{_ROLE}\s*<\|end_header_id\|>"
        rf"|<start_of_turn>[ \t]*(?:system|model){_EOL}",
    ),
    # Matches the shape of the judge's 128-bit envelope nonce; it cannot know the real nonce.
    _rule("envelope_forgery", "high", r"</?data-[0-9a-f]{32}>"),
    _rule(
        "chat_template_token",
        "medium",
        r"<\|(?:im_start|im_end|eot_id|start_header_id|end_header_id|endoftext|system|user|assistant)\|>"
        r"|\[/?INST\]|<</?SYS>>|<start_of_turn>|<end_of_turn>",
    ),
    _rule(
        "role_marker",
        "medium",
        rf"^[ \t]*{_ROLE}[ \t]*:|###[ \t]*(?:system|instructions?)\b|</?system>",
    ),
    _rule(
        "tool_forgery",
        "medium",
        r"</?(?:tool_call|tool_result|function_calls?|function_results?)>"
        r'|"(?:tool_calls|function_call)"\s*:',
    ),
    _rule(
        "ignore_instructions",
        "medium",
        rf"{_START}(?:ignore|disregard|forget|override){_END}[^.\n]{{0,40}}?"
        rf"{_START}(?:instructions?|prompts?|rules|guidelines|directions){_END}",
    ),
    _rule(
        "reveal_prompt",
        "medium",
        rf"{_START}(?:reveal|print|show|repeat|output|leak){_END}[^.\n]{{0,30}}?"
        rf"{_START}(?:system prompt|initial instructions|hidden instructions"
        rf"|your instructions){_END}",
    ),
    _rule(
        "persona_override",
        "medium",
        rf"{_START}(?:do anything now|DAN mode|developer mode (?:enabled|on)"
        rf"|jailbreak(?:ed)? mode){_END}",
    ),
)

FINDING_RULES: tuple[FindingRule, ...] = (
    # Caps stopped inspection, so the unread remainder could hold anything.
    FindingRule("incomplete_inspection", "high", tuple(sorted(INCOMPLETE_KEYS)), 1),
    FindingRule("invisible_chars", "medium", ("invisible",), 3),
    FindingRule("bidi_controls", "medium", ("bidi",), 1),
    FindingRule("homoglyphs", "medium", ("homoglyph",), 3),
    FindingRule("encoded_payload", "low", ("hex", "base64", "rot13"), 1),
)


def match_rules(prepared: Prepared) -> list[Match]:
    """Every rule that fires on any view of the request, sorted by id.

    The raw view is scanned too when normalization changed the text, because a cap can cut the
    normalized view short of a marker that the raw text still shows. Intermediate views are
    scanned so a marker exposed by one pass cannot be erased by the next.
    """
    normalized = prepared.normalized
    raw = prepared.raw[:MAX_INPUT_CHARS]
    views = [normalized.text, *normalized.views]
    if normalized.changed or raw != prepared.raw:
        views.append(raw)
    matches = [
        Match(rule.id, rule.severity)
        for rule in TEXT_RULES
        if any(rule.pattern.search(view) for view in views)
    ]
    matches += [
        Match(rule.id, rule.severity)
        for rule in FINDING_RULES
        if sum(normalized.findings.get(key, 0) for key in rule.keys) >= rule.threshold
    ]
    return sorted(matches, key=lambda m: m.id)


def top_severity(matches: list[Match]) -> Severity | None:
    """The most trusted severity among ``matches``, or None when nothing fired."""
    if not matches:
        return None
    return min((m.severity for m in matches), key=_SEVERITY_ORDER.__getitem__)
