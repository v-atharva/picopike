"""Undo common obfuscation so rules and models see what an attacker meant to write.

Work is bounded at every step, so a hostile input costs at most a fixed amount:

* the input is cut to ``limit`` characters (``MAX_CHARS`` by default; a request is admitted at
  ``MAX_INPUT_CHARS`` by ``picopike.inputs.prepare``) before anything else runs;
* NFKC runs only on the prefix whose decomposition fits in ``MAX_CHARS``, so an expansion bomb
  cannot allocate more than that;
* each later pass works on at most ``MAX_CHARS`` characters, for at most ``MAX_ROUNDS`` passes
  plus one pass that checks whether a further one would still change the text. Each pass decodes
  every payload present at its start, so independent payloads advance together.

Hitting any bound is reported (``truncated`` or ``depth_limited``) and makes ``complete`` False.
``complete`` means no bound stopped the supported transformations; it does not mean every
possible encoding was recognised. Output never exceeds ``MAX_CHARS``, so a complete result is
always a valid input that normalizes to itself.
"""

from __future__ import annotations

import base64
import binascii
import itertools
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

MAX_INPUT_CHARS = 32_768
MAX_CHARS = 65_536
MAX_ROUNDS = 4
# Bumped whenever the set of transformations or the character profile changes, for provenance.
PROFILE = "normalize-v3/unicode-15.1.0"
FINDING_KEYS = frozenset(
    {
        "invisible",
        "bidi",
        "compat",
        "homoglyph",
        "hex",
        "base64",
        "rot13",
        "truncated",
        "depth_limited",
    }
)
INCOMPLETE_KEYS = frozenset({"truncated", "depth_limited"})

_BIDI = "\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069"
# Every format character (Unicode 15.1, general category Cf) plus the invisible marks and
# fillers attackers use to split words: the combining grapheme joiner, variation selectors,
# Mongolian free variation selectors and Hangul fillers. Bidi controls are listed separately
# because they are counted separately.
_INVISIBLE = (
    "\u00ad\u034f\u0600-\u0605\u06dd\u070f\u0890\u0891\u08e2\u115f\u1160"
    "\u180b-\u180f\u200b-\u200d\u2060-\u2064\u206a-\u206f\u3164\ufe00-\ufe0f"
    "\ufeff\uffa0\ufff9-\ufffb\U000110bd\U000110cd\U00013430-\U0001343f"
    "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0001\U000e0020-\U000e007f"
    "\U000e0100-\U000e01ef"
)
_INVISIBLE_RUN = re.compile(f"[{_INVISIBLE}{_BIDI}]+")
_BIDI_CHAR = re.compile(f"[{_BIDI}]")
_SOFT_HYPHEN = "\u00ad"

# Cyrillic and Greek letters that render like Latin ones.
_HOMOGLYPHS = {
    "\u0430": "a",
    "\u0441": "c",
    "\u0435": "e",
    "\u04bb": "h",
    "\u0456": "i",
    "\u0458": "j",
    "\u043e": "o",
    "\u0440": "p",
    "\u0455": "s",
    "\u0445": "x",
    "\u0443": "y",
    "\u0501": "d",
    "\u051b": "q",
    "\u051d": "w",
    "\u04cf": "l",
    "\u0410": "A",
    "\u0412": "B",
    "\u0421": "C",
    "\u0415": "E",
    "\u041d": "H",
    "\u0406": "I",
    "\u0408": "J",
    "\u041a": "K",
    "\u041c": "M",
    "\u041e": "O",
    "\u0420": "P",
    "\u0405": "S",
    "\u0422": "T",
    "\u0425": "X",
    "\u0423": "Y",
    "\u03b1": "a",
    "\u03b9": "i",
    "\u03bd": "v",
    "\u03bf": "o",
    "\u03c1": "p",
    "\u0391": "A",
    "\u0392": "B",
    "\u0395": "E",
    "\u0396": "Z",
    "\u0397": "H",
    "\u0399": "I",
    "\u039a": "K",
    "\u039c": "M",
    "\u039d": "N",
    "\u039f": "O",
    "\u03a1": "P",
    "\u03a4": "T",
    "\u03a5": "Y",
    "\u03a7": "X",
}
_FOLD = str.maketrans(_HOMOGLYPHS)
_HOMOGLYPH_CHARS = frozenset(_HOMOGLYPHS)
_WORD = re.compile(r"[^\W_]+")

# A hex run next to "+" or "/", or followed by "=" that reads as padding, may be the head of a
# base64 payload, so it is left to the base64 alternative; hex inside a base64-shaped run is
# decoded only if the run itself is not base64, as in "key=<hex>/next".
_HEX_RUN = re.compile(
    r"(?<![0-9A-Za-z+/])(?:[0-9A-Fa-f]{2}){8,}(?![0-9A-Za-z+/])(?!={1,2}(?![0-9A-Za-z+/=]))"
)
_HEX_PIECE = re.compile(r"(?<![0-9A-Za-z])(?:[0-9A-Fa-f]{2}){8,}(?![0-9A-Za-z])")
# These end a line for ``str.splitlines`` and for renderers, so they must end one here too.
_LINE_CHARS = "\n\r\v\f\x1c-\x1e\x85\u2028\u2029"
_LINE_BOUNDARY = re.compile(f"[{_LINE_CHARS}]")
# Indented or space-padded lines (YAML block scalars, Markdown code blocks) still join; spaces
# are outside both alphabets, so a seam is consumed in exactly one way.
_SEAM = re.compile(f"[ \t]*(?:\r\n|[{_LINE_CHARS}])[ \t]*")
_BLOCK_GAP = re.compile(f"[ \t{_LINE_CHARS}]")
# Standard encoders wrap at 76 columns, so a block spans lines of whole 4-character groups;
# decoding each line alone would let a seam split a marker in the decoded text.
_BASE64_BLOCK = (
    r"(?<![A-Za-z0-9+/])(?:(?:[A-Za-z0-9+/]{4}){4,}(?:" + _SEAM.pattern + r"))+[A-Za-z0-9+/]{2,}"
    r"={0,2}(?![A-Za-z0-9+/=])"
)
_BASE64_LINE = r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/=])"
_LINE_PAYLOAD = re.compile(f"(?P<hex>{_HEX_RUN.pattern})|(?P<base64>{_BASE64_LINE})")
# The block alternative comes first, so a first line made only of hex digits cannot split it.
_PAYLOAD = re.compile(f"(?P<block>{_BASE64_BLOCK})|{_LINE_PAYLOAD.pattern}")
_LETTER_RUN = re.compile(r"[^\W\d_]{3,}")
# Decoded payloads up to this size are put in canonical form (invisible marks removed, NFKC,
# look-alikes folded) before the readability check, so any mix of the disguises this module
# undoes is recognised inside an encoding. Larger payloads are checked as they are.
_PROBE_CHARS = 2_048
# rot13 is only undone when it spells words attackers use, since any word "decodes" to something.
# The list covers every keyword the phrase rules look for, so a rot13 phrase can be recognised.
_TRIGGER_WORDS = frozenset(
    {
        "anything",
        "bypass",
        "dan",
        "developer",
        "directions",
        "disregard",
        "do",
        "enabled",
        "forget",
        "guidelines",
        "hidden",
        "ignore",
        "initial",
        "instruction",
        "instructions",
        "jailbreak",
        "jailbreaked",
        "jailbroken",
        "leak",
        "mode",
        "now",
        "on",
        "output",
        "override",
        "password",
        "previous",
        "print",
        "prior",
        "prompt",
        "prompts",
        "repeat",
        "reveal",
        "rules",
        "secret",
        "show",
        "system",
        "unrestricted",
        "your",
    }
)
_TRIGGER = re.compile(
    r"(?<![^\W_])(?:" + "|".join(sorted(_TRIGGER_WORDS)) + r")(?![^\W_])", re.IGNORECASE
)
_ASCII_WORD = re.compile(r"[A-Za-z]{4,}")
_ROT13 = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
)
_SPACES = re.compile(r"[^\S\n]+")
_LINE_BREAKS = re.compile(r"\s*\n\s*")


@dataclass(frozen=True)
class Normalized:
    """The cleaned text and what was found in it; findings hold counts, never input text.

    ``changed`` says whether the text differs from the input beyond whitespace (or was cut),
    which is when a second scoring view is worth its cost. ``findings`` is the evidence and is
    read-only, because every lane shares it; ``complete`` is fixed at construction for the same
    reason. ``views`` keeps each intermediate text a pass produced, so a marker exposed by one
    pass and altered by the next is still visible to the rules; there are at most ``MAX_ROUNDS``.
    """

    text: str
    findings: Mapping[str, int]
    changed: bool
    complete: bool
    views: tuple[str, ...] = ()


def normalize(text: str, *, limit: int = MAX_CHARS) -> Normalized:
    """Clean ``text`` until it stops changing or a bound is hit.

    Results with ``complete`` set are fixed points: normalizing them again changes nothing.
    """
    limit = min(limit, MAX_CHARS)
    findings: Counter[str] = Counter()
    cut = len(text) > limit
    if cut:
        findings["truncated"] = 1
        text = text[:limit]
    current = text
    views: list[str] = []
    inert: set[str] = set()
    for _ in range(MAX_ROUNDS):
        cleaned = _one_pass(current, findings, inert)
        if cleaned == current:
            break
        views.append(current)
        current = cleaned
    else:
        if _one_pass(current, Counter(), inert) != current:
            findings["depth_limited"] = 1
    kept = {k: v for k, v in findings.items() if v}
    return Normalized(
        text=current,
        findings=MappingProxyType(kept),
        changed=cut or current != _collapse_whitespace(text),
        complete=INCOMPLETE_KEYS.isdisjoint(kept),
        views=tuple(views[1:]),
    )


def has_encoded_run(text: str) -> bool:
    """Whether ``text`` contains a hex or base64 run, which could decode into costly text."""
    return _PAYLOAD.search(text) is not None


def _one_pass(text: str, findings: Counter[str], inert: set[str]) -> str:
    text = _strip_invisible(text, findings)
    text = _compat(text, findings)
    text = _fold_homoglyphs(text, findings)
    text = _decode_payloads(text, findings, inert)
    return _collapse_whitespace(text)


def _strip_invisible(text: str, findings: Counter[str]) -> str:
    for run in _INVISIBLE_RUN.finditer(text):
        start, end = run.start(), run.end()
        chars = run.group()
        bidi = len(_BIDI_CHAR.findall(chars))
        findings["bidi"] += bidi
        splits_word = (
            start > 0 and end < len(text) and text[start - 1].isalnum() and text[end].isalnum()
        )
        if splits_word:
            # Soft hyphens split words innocently in text copied from PDFs.
            findings["invisible"] += len(chars) - bidi - chars.count(_SOFT_HYPHEN)
    return _INVISIBLE_RUN.sub("", text)


def _compat(text: str, findings: Counter[str]) -> str:
    if text.isascii():
        return text
    counts = Counter(text)
    expansion = {ch: len(unicodedata.normalize("NFKD", ch)) for ch in counts if not ch.isascii()}
    if sum(n * expansion.get(ch, 1) for ch, n in counts.items()) > MAX_CHARS:
        # Only normalize the prefix whose decomposition fits; the rest is reported unread.
        sizes = itertools.accumulate(expansion.get(ch, 1) for ch in text)
        fits = sum(1 for _ in itertools.takewhile(lambda size: size <= MAX_CHARS, sizes))
        findings["truncated"] = 1
        text = text[:fits]
        counts = Counter(text)
    folded = unicodedata.normalize("NFKC", text)
    if folded != text:
        findings["compat"] += sum(
            n
            for ch, n in counts.items()
            if not ch.isascii() and not ch.isspace() and unicodedata.normalize("NFKC", ch) != ch
        )
    return folded


def _fold_homoglyphs(text: str, findings: Counter[str]) -> str:
    if _HOMOGLYPH_CHARS.isdisjoint(text):
        return text

    def fold(match: re.Match[str]) -> str:
        # Fold a word only if its non-ASCII letters are all look-alikes: a genuine Cyrillic or
        # Greek letter means the word is real text in that script, not a disguise.
        word = match.group()
        lookalikes = sum(ch in _HOMOGLYPHS for ch in word)
        native = any(not ch.isascii() and ch.isalpha() and ch not in _HOMOGLYPHS for ch in word)
        if not lookalikes or native or len(word) < 2:
            return word
        findings["homoglyph"] += lookalikes
        return word.translate(_FOLD)

    return _WORD.sub(fold, text)


def _decode_payloads(text: str, findings: Counter[str], inert: set[str]) -> str:
    # Every payload present at the start of the pass is decoded in one scan, but decoded text is
    # not rescanned until the next pass has stripped, folded and normalized it: an inner layer is
    # never half-read, and independent payloads do not wait for each other.
    before = findings["hex"] + findings["base64"]
    text = _PAYLOAD.sub(lambda match: _decode_once(match, findings, inert), text)
    if findings["hex"] + findings["base64"] > before:
        return text
    return _decode_rot13(text, findings)


def _decode_once(match: re.Match[str], findings: Counter[str], inert: set[str]) -> str:
    """Decode ``match`` unless an earlier pass found that its run decodes to nothing.

    A run that decodes nothing is reproduced exactly and its outcome depends only on its own text,
    so remembering it saves every later pass from repeating the work.
    """
    run = match.group()
    if run in inert:
        return run
    before = findings["hex"] + findings["base64"]
    decoded = _decode_match(match, findings)
    if findings["hex"] + findings["base64"] == before:
        inert.add(run)
    return decoded


def _decode_match(match: re.Match[str], findings: Counter[str]) -> str:
    if match.group("block"):
        return _decode_block(match, findings)
    return _decode_line(match, findings)


def _decode_line(match: re.Match[str], findings: Counter[str]) -> str:
    text, start, end = match.string, match.start(), match.end()
    kind = "hex" if match.group("hex") else "base64"
    decoded = (_from_hex if kind == "hex" else _from_base64)(match.group())
    if decoded is None and kind == "hex":
        # Base64 text can be made only of hex digits, and the hex alternative matches first.
        kind, decoded = "base64", _from_base64(match.group())
    elif decoded is None:
        return _sub_within(_HEX_PIECE, text, start, end, lambda m: _decode_hex_piece(m, findings))
    if decoded is None:
        return match.group()
    findings[kind] += 1
    return _as_word(decoded, text, start, end)


def _decode_hex_piece(match: re.Match[str], findings: Counter[str]) -> str:
    decoded = _from_hex(match.group())
    if decoded is None:
        return match.group()
    findings["hex"] += 1
    return _as_word(decoded, match.string, match.start(), match.end())


def _decode_block(match: re.Match[str], findings: Counter[str]) -> str:
    """Decode a run of wrapped lines block by block, keeping the line breaks between blocks.

    The lines after each block are read as the next block, so a later payload in the same run is
    still found. Each attempt consumes at least one line and a line takes part in at most two
    blocks, so the work stays linear in the run's length.
    """
    text, run_start, run_end = match.string, match.start(), match.end()
    seams = list(_SEAM.finditer(text, run_start, run_end))
    # Irregular rewraps have no single width, so the whole run is tried before the walk, also
    # without a final line that may be ordinary text; that line is still read as a payload.
    kind, whole = _from_block(match.group())
    if whole is not None:
        findings[kind] += 1
        return _as_word(whole, text, run_start, run_end)
    final = seams[-1]
    kind, head = _from_block(text[run_start : final.start()])
    if head is not None:
        findings[kind] += 1
        tail = _sub_within(
            _LINE_PAYLOAD, text, final.end(), run_end, lambda m: _decode_line(m, findings)
        )
        return _as_word(head, text, run_start, final.start()) + final.group() + tail
    starts = [run_start, *(seam.end() for seam in seams)]
    ends = [*(seam.start() for seam in seams), run_end]
    lines = list(zip(starts, ends, strict=True))
    parts: list[str] = []
    last, first = run_start, 0
    while first < len(lines):
        stop, decoded = _decode_wrapped(text, lines, first)
        start, end = lines[first][0], lines[stop - 1][1]
        if decoded is None:
            # Not wrapped base64 after all: each line may still be a payload of its own.
            decoded = _sub_within(
                _LINE_PAYLOAD, text, start, end, lambda m: _decode_line(m, findings)
            )
        else:
            findings["base64"] += 1
            decoded = _as_word(decoded, text, start, end)
        parts += [text[last:start], decoded]
        last, first = end, stop
    return "".join(parts)


def _decode_wrapped(text: str, lines: list[tuple[int, int]], first: int) -> tuple[int, str | None]:
    """Where the block starting at line ``first`` ends, and its decoded text if it decodes.

    The block is the leading lines as wide as its first, plus a final line no wider. That final
    line may be ordinary text that happens to be whole base64 groups, so the block is also tried
    without it.
    """
    width = lines[first][1] - lines[first][0]
    stop = first + 1
    while stop < len(lines) and lines[stop][1] - lines[stop][0] == width:
        stop += 1
    if stop < len(lines) and lines[stop][1] - lines[stop][0] <= width:
        stop += 1
    for end in (stop, stop - 1) if stop - first > 1 else (stop,):
        decoded = _from_base64(text[lines[first][0] : lines[end - 1][1]])
        if decoded is not None:
            return end, decoded
    return stop, None


def _sub_within(
    pattern: re.Pattern[str],
    text: str,
    start: int,
    end: int,
    replace: Callable[[re.Match[str]], str],
) -> str:
    """``pattern.sub(replace, text[start:end])``, but each match still sees the text around it."""
    parts: list[str] = []
    last = start
    for match in pattern.finditer(text, start, end):
        parts += [text[last : match.start()], replace(match)]
        last = match.end()
    parts.append(text[last:end])
    return "".join(parts)


def _as_word(decoded: str, text: str, start: int, end: int) -> str:
    """``decoded`` in place of ``text[start:end]``, spaced apart from any word it touches.

    Keeping the payload a separate word means "x_<payload>_y" cannot defeat word boundaries.
    """
    before = start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_")
    after = end < len(text) and (text[end].isalnum() or text[end] == "_")
    return " " * before + decoded + " " * after


def _from_hex(run: str) -> str | None:
    try:
        return _as_text(bytes.fromhex(run))
    except ValueError:
        return None


def _from_block(run: str) -> tuple[str, str | None]:
    """The kind and decoded text of a wrapped run: base64, or plain hex as ``xxd -p`` wraps it."""
    decoded = _from_base64(run)
    if decoded is not None:
        return "base64", decoded
    return "hex", _from_hex(_BLOCK_GAP.sub("", run))


def _from_base64(run: str) -> str | None:
    # Padding is often dropped by hand; restore it rather than let the payload through.
    body = _BLOCK_GAP.sub("", run).rstrip("=")
    if len(body) % 4 == 1:
        return None
    try:
        return _as_text(base64.b64decode(body + "=" * (-len(body) % 4), validate=True))
    except (binascii.Error, ValueError):
        return None


def _as_text(raw: bytes) -> str | None:
    """The decoded payload if it is readable text, else None.

    Hashes and ids decode to binary noise, so a payload must be valid UTF-8 and fully printable
    once invisible controls are set aside. It must also contain a word-like run of at least three
    letters or another encoded run, so nested encodings keep unwrapping. Punctuation is allowed
    freely, because templates, JSON and code are punctuation-heavy.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    probe = _INVISIBLE_RUN.sub("", text)
    if len(probe) <= _PROBE_CHARS:
        probe = unicodedata.normalize("NFKC", probe).translate(_FOLD)
    if len(probe) < 4 or not all(ch.isprintable() or ch.isspace() for ch in probe):
        return None
    return text if _PAYLOAD.search(probe) or _LETTER_RUN.search(probe) else None


def _decode_rot13(text: str, findings: Counter[str]) -> str:
    if not _ASCII_WORD.search(text):
        return text
    # rot13 maps letters to letters, so word boundaries line up in both strings.
    rotated = text.translate(_ROT13)
    spans = [
        m.span() for m in _TRIGGER.finditer(rotated) if not _TRIGGER.fullmatch(text, *m.span())
    ]
    # Short triggers ("on", "do") are rot13 of common words and abbreviations ("BA", "QB"), and
    # one abbreviation can repeat ("QnA" is "DaN"), so rotating needs two different longer ones.
    if len({rotated[start:end].lower() for start, end in spans if end - start >= 3}) < 2:
        return text
    findings["rot13"] += len(spans)
    parts: list[str] = []
    last = 0
    for start, end in spans:
        parts += [text[last:start], rotated[start:end]]
        last = end
    parts.append(text[last:])
    return "".join(parts)


def _collapse_whitespace(text: str) -> str:
    # Treating a line boundary as a space would hide role markers that must start a line.
    text = _LINE_BOUNDARY.sub("\n", text.replace("\r\n", "\n"))
    text = _SPACES.sub(" ", text)
    return _LINE_BREAKS.sub("\n", text).strip()
