"""
Reducers: small functions that each shrink text in one specific, meaning-safe way.

Every reducer has the same simple shape::

    def some_reducer(text: str) -> str:
        ...  # return a smaller (or equal) version of the text

Keeping them tiny and single-purpose means we can test them one at a time and
chain them together in any order (see engine.py).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 1. Whitespace normaliser  (100% safe — never changes meaning)
# ---------------------------------------------------------------------------


def normalize_whitespace(text: str) -> str:
    """Collapse wasteful whitespace.

    - turn tabs into a single space
    - collapse runs of spaces/tabs into one space
    - strip trailing spaces at the end of each line
    - collapse 3+ blank lines down to a single blank line
    - strip leading/trailing blank space for the whole text
    """
    # Normalise Windows/Mac line endings to "\n" first.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse runs of spaces and tabs (but not newlines) into one space.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove trailing spaces on each line.
    text = re.sub(r" *\n", "\n", text)

    # Collapse 3 or more newlines into two (i.e. at most one blank line).
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ---------------------------------------------------------------------------
# 2. Filler remover  (meaning-preserving — drops politeness / padding words)
# ---------------------------------------------------------------------------

# Multi-word polite padding. Order matters: longer phrases first so we don't
# leave dangling fragments. Matched case-insensitively.
_FILLER_PHRASES = [
    "thank you so much",
    "thanks so much",
    "thank you very much",
    "as you can see",
    "it is important to note that",
    "it should be noted that",
    "needless to say",
    "for what it's worth",
    "at the end of the day",
    "please note that",
    "i would like you to",
    "i want you to",
    "could you please",
    "can you please",
    "would you kindly",
    "please kindly",
]

# Single filler adverbs/words that rarely change meaning when dropped.
_FILLER_WORDS = [
    "please",
    "kindly",
    "really",
    "very",
    "basically",
    "actually",
    "simply",
    "just",
    "literally",
    "essentially",
]


def remove_filler(text: str) -> str:
    """Remove common politeness/padding words and phrases.

    This is 'meaning-preserving' rather than perfectly lossless: an LLM reading
    the result gets the same instruction, just without the social padding.
    """
    for phrase in _FILLER_PHRASES:
        text = re.sub(re.escape(phrase), "", text, flags=re.IGNORECASE)

    for word in _FILLER_WORDS:
        # \b = word boundary, so "just" won't nuke "adjust".
        text = re.sub(rf"\b{re.escape(word)}\b", "", text, flags=re.IGNORECASE)

    # Removing words leaves litter behind — tidy it up.
    text = re.sub(r"[ \t]+", " ", text)          # collapse double spaces
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # no space before punctuation
    text = _tidy_punctuation(text)
    return normalize_whitespace(text)


def _tidy_punctuation(text: str) -> str:
    """Clean up orphaned punctuation left behind after removing words."""
    # A sentence-ender immediately followed by a comma/semicolon: ". ," -> "."
    text = re.sub(r"([.!?])\s*[,;:]+", r"\1", text)
    # A comma/semicolon left at the very start, or right after a sentence end.
    text = re.sub(r"(^|[.!?]\s+)[,;:]+\s*", r"\1", text)
    # Collapse repeated commas: ",," -> ","
    text = re.sub(r",\s*,+", ",", text)
    return text


# ---------------------------------------------------------------------------
# 3. Duplicate-sentence remover  (100% safe — drops exact repeats)
# ---------------------------------------------------------------------------


def remove_duplicate_sentences(text: str) -> str:
    """Drop sentences that repeat an earlier sentence word-for-word.

    We split on sentence-ending punctuation, keep the first occurrence of each
    sentence, and skip later exact duplicates (ignoring case and surrounding
    spaces). Order of the survivors is preserved.
    """
    # Split into sentences while keeping the punctuation that ended them.
    parts = re.split(r"(?<=[.!?])\s+", text)

    seen: set[str] = set()
    kept: list[str] = []
    for sentence in parts:
        key = sentence.strip().lower()
        if not key:
            continue
        if key in seen:
            continue  # exact repeat — skip it
        seen.add(key)
        kept.append(sentence.strip())

    return " ".join(kept)
