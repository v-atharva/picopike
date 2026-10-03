"""One request's text, normalized once and shared by every lane that can reuse it."""

from __future__ import annotations

from dataclasses import dataclass

from picopike.normalize import MAX_INPUT_CHARS, Normalized, has_encoded_run, normalize

# Text this short, ASCII-only and free of encoded runs normalizes in about a millisecond, so
# it can be prepared inline. Raw length alone is not enough: a short string can still expand or
# decode into expensive text, so anything else goes to the shared worker.
INLINE_CHARS = 2_048


@dataclass(frozen=True)
class Prepared:
    """The raw text alongside its normalized view, so findings survive between stages."""

    raw: str
    normalized: Normalized
    lang: str | None


def prepare(text: str, *, lang: str | None = None) -> Prepared:
    """Admit at most ``MAX_INPUT_CHARS`` of ``text`` and normalize it once."""
    return Prepared(raw=text, normalized=normalize(text, limit=MAX_INPUT_CHARS), lang=lang)


def cheap_to_prepare(text: str) -> bool:
    """Whether preparing ``text`` is cheap enough to run on the event loop."""
    return len(text) <= INLINE_CHARS and text.isascii() and not has_encoded_run(text)


def cheap_to_match(prepared: Prepared) -> bool:
    """Whether matching rules on every view of ``prepared`` is cheap enough to run inline."""
    sizes = [len(prepared.raw), len(prepared.normalized.text)]
    sizes += [len(view) for view in prepared.normalized.views]
    return sum(sizes) <= 2 * INLINE_CHARS
