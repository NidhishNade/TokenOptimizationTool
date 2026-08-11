"""
Advisor: structural *suggestions* for saving tokens — it never rewrites text.

The biggest savings often aren't about wording at all. If you send the same big
block of text (a system prompt, instructions, a document) on every API call, you
pay for it every single time. Providers like Anthropic offer **prompt caching**:
mark that static block once and reuse it cheaply. This module spots such blocks
and tells you about them, so you can restructure your calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .counter import count_tokens


@dataclass
class Suggestion:
    """One piece of advice for the user."""

    kind: str          # e.g. "repeated-block", "cacheable-prefix"
    message: str       # human-readable explanation
    tokens_involved: int


def _paragraphs(text: str) -> list[str]:
    """Split text into paragraphs on blank lines."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def find_repeated_blocks(text: str, min_tokens: int = 8) -> list[Suggestion]:
    """Find paragraphs that appear more than once (candidates to define once).

    A large block repeated N times is paid for N times. Defining it once (a
    variable, a cached prefix) removes the duplication at the source.
    """
    paragraphs = _paragraphs(text)
    counts: dict[str, int] = {}
    for para in paragraphs:
        key = " ".join(para.lower().split())  # normalise whitespace for comparison
        counts[key] = counts.get(key, 0) + 1

    suggestions: list[Suggestion] = []
    for key, count in counts.items():
        if count < 2:
            continue
        tokens = count_tokens(key)
        if tokens < min_tokens:
            continue
        wasted = tokens * (count - 1)  # everything past the first copy is waste
        preview = (key[:50] + "…") if len(key) > 50 else key
        suggestions.append(
            Suggestion(
                kind="repeated-block",
                message=(
                    f'A block of ~{tokens} tokens appears {count} times '
                    f'("{preview}"). Define it once to save ~{wasted} tokens.'
                ),
                tokens_involved=wasted,
            )
        )
    return suggestions


def advise(text: str, min_tokens: int = 8) -> list[Suggestion]:
    """Return all structural suggestions for a piece of text."""
    return find_repeated_blocks(text, min_tokens=min_tokens)
