"""
Text normalization utilities for Chinese news articles.

Handles:
  - Fullwidth ↔ halfwidth conversion
  - Traditional / simplified unification (→ zh-Hant)
  - Punctuation normalization
  - URL / HTML tag stripping
  - Whitespace collapsing
  - Duplicate line / paragraph removal
"""

from __future__ import annotations

import re
import unicodedata

try:
    import opencc
    _OCC_S2T = opencc.OpenCC("s2t")
    _OCC_AVAILABLE = True
except ImportError:
    _OCC_S2T = None
    _OCC_AVAILABLE = False

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
_RE_URL = re.compile(r"https?://\S+")
_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_WHITESPACE = re.compile(r"\s+")
_RE_SPECIAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Fullwidth → halfwidth mapping for common chars
_FULLWIDTH_MAP = {chr(i): chr(i - 0xFEE0) for i in range(0xFF01, 0xFF5F + 1)}
_FULLWIDTH_MAP["　"] = " "  # fullwidth space


def normalize(text: str, *,
              unify_width: bool = True,
              convert_trad: bool = True,
              strip_urls: bool = True,
              strip_html: bool = True,
              strip_special: bool = True,
              collapse_ws: bool = True,
              dedup_paragraphs: bool = True) -> str:
    """
    Normalize a Chinese text string.

    Args:
        text: Raw input text.
        unify_width: Convert fullwidth chars to halfwidth.
        convert_trad: Convert simplified → traditional (zh-Hant).
        strip_urls: Remove HTTP(S) URLs.
        strip_html: Remove HTML tags.
        strip_special: Remove control characters.
        collapse_ws: Collapse consecutive whitespace to single space.
        dedup_paragraphs: Remove consecutive duplicate paragraphs.

    Returns:
        Normalized text.
    """
    if not text or not text.strip():
        return ""

    # 1. Strip HTML
    if strip_html:
        text = _RE_HTML_TAG.sub("", text)

    # 2. Strip URLs
    if strip_urls:
        text = _RE_URL.sub("", text)

    # 3. Fullwidth → halfwidth
    if unify_width:
        text = "".join(_FULLWIDTH_MAP.get(c, c) for c in text)

    # 4. Simplified → traditional
    if convert_trad and _OCC_AVAILABLE:
        text = _OCC_S2T.convert(text)

    # 5. Strip control chars
    if strip_special:
        text = _RE_SPECIAL.sub("", text)

    # 6. Collapse whitespace
    if collapse_ws:
        text = _RE_WHITESPACE.sub(" ", text)

    # 7. Deduplicate consecutive paragraphs
    if dedup_paragraphs:
        paragraphs = text.split("\n")
        seen: set[str] = set()
        unique = []
        for p in paragraphs:
            p_stripped = p.strip()
            if p_stripped and p_stripped not in seen:
                seen.add(p_stripped)
                unique.append(p_stripped)
        text = "\n".join(unique)

    return text.strip()


def dedup_lines(lines: list[str]) -> list[str]:
    """Remove exact duplicate lines while preserving order."""
    seen: set[str] = set()
    result = []
    for line in lines:
        s = line.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(line)
    return result
