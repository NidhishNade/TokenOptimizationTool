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
    # Collapse repeated sentence-enders: ". ." or ".." -> "."
    text = re.sub(r"([.!?])(\s*[.!?])+", r"\1", text)
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


# ---------------------------------------------------------------------------
# 3.5 Wordy-phrase simplifier  (100% safe — swaps bloated phrases for exact,
#     shorter synonyms. Every replacement was verified to reduce cl100k tokens.)
# ---------------------------------------------------------------------------

# Verbose connective/qualifier phrases → a shorter word that means the same
# thing. Longest keys are applied first so we don't leave fragments behind.
# These are lossless in meaning (unlike `abbreviate`, which uses shorthand), so
# this reducer is safe enough to live in the default pipeline.
_WORDY_PHRASES = {
    "in spite of the fact that": "although",
    "despite the fact that": "although",
    "due to the fact that": "because",
    "owing to the fact that": "because",
    "in view of the fact that": "because",
    "for the reason that": "because",
    "on the grounds that": "because",
    "at this point in time": "now",
    "at this moment in time": "now",
    "at the present time": "now",
    "for the purpose of": "for",
    "in the event that": "if",
    "in the near future": "soon",
    "in this day and age": "today",
    "a large number of": "many",
    "a great number of": "many",
    "a wide variety of": "many",
    "a variety of": "various",
    "a sufficient amount of": "enough",
    "the majority of": "most",
    "a majority of": "most",
    "on a daily basis": "daily",
    "on a regular basis": "regularly",
    "on a weekly basis": "weekly",
    "at all times": "always",
    "in most cases": "usually",
    "in many cases": "often",
    "has the ability to": "can",
    "have the ability to": "can",
    "with regard to": "about",
    "with respect to": "about",
    "in regard to": "about",
    "in relation to": "about",
    "with reference to": "about",
    "with the exception of": "except",
    "in the absence of": "without",
    "in conjunction with": "with",
    "in addition to": "besides",
    "by means of": "via",
    "in close proximity to": "near",
    "during the course of": "during",
    "in the course of": "during",
    "until such time as": "until",
    "the way in which": "how",
    "take into consideration": "consider",
    "take into account": "consider",
    "come to a conclusion": "conclude",
    "make a decision": "decide",
    "as a matter of fact": "in fact",
    "each and every": "every",
    "as well as": "and",
    "is going to": "will",
    "are going to": "will",
    "in order to": "to",
    "is able to": "can",
    "are able to": "can",
    "in spite of": "despite",
    "the fact that": "that",
    "prior to": "before",
    "subsequent to": "after",
    "a number of": "several",
}


def simplify_phrases(text: str) -> str:
    """Replace wordy phrases with shorter, exact-meaning equivalents (safe).

    e.g. "due to the fact that" -> "because", "in order to" -> "to". Every swap
    keeps the meaning intact, so this runs in the default pipeline.
    """
    # Longest phrases first so "with regard to" wins before any shorter overlap.
    for phrase in sorted(_WORDY_PHRASES, key=len, reverse=True):
        text = re.sub(
            re.escape(phrase), _WORDY_PHRASES[phrase], text, flags=re.IGNORECASE
        )
    text = re.sub(r"[ \t]+", " ", text)
    # A swap at the start of a sentence can leave the replacement lowercased.
    return _capitalize_sentences(text)


# ===========================================================================
# ADVANCED / OPT-IN reducers (Phase 3).
# These save more but can change meaning, so they are NOT in the safe default
# pipeline — the caller must ask for them explicitly.
# ===========================================================================

# ---------------------------------------------------------------------------
# 4. Abbreviator  (🟡 medium risk — the model must understand the shorthand)
# ---------------------------------------------------------------------------

# Multi-word phrases first (longer matches win). value = short form.
# NOTE: every mapping here was checked against the cl100k tokenizer and only
# kept if it does NOT increase the token count. Tempting swaps like
# "for example"->"e.g.", "with"->"w/", "without"->"w/o" and "number"->"no."
# were removed because they actually make the text *longer* in tokens.
_ABBREVIATION_PHRASES = {
    "as soon as possible": "ASAP",
    "with respect to": "re:",
    "that is to say": "i.e.",
    "in order to": "to",
    "a lot of": "many",
    "due to the fact that": "because",
    "in the event that": "if",
}

# Single words. Includes some aggressive ones (you -> u) on purpose.
_ABBREVIATION_WORDS = {
    "because": "bc",
    "approximately": "approx",
    "information": "info",
    "documentation": "docs",
    "application": "app",
    "versus": "vs",
    "and": "&",
    "you": "u",
    "your": "ur",
    "are": "r",
}


def abbreviate(text: str) -> str:
    """Replace common words/phrases with shorter forms (opt-in, aggressive).

    Saves tokens but relies on the model understanding the shorthand, so it can
    change meaning. Off by default — pass it explicitly if you want it.
    """
    for phrase, short in _ABBREVIATION_PHRASES.items():
        text = re.sub(re.escape(phrase), short, text, flags=re.IGNORECASE)

    for word, short in _ABBREVIATION_WORDS.items():
        text = re.sub(rf"\b{re.escape(word)}\b", short, text, flags=re.IGNORECASE)

    return normalize_whitespace(text)


# ---------------------------------------------------------------------------
# 5. Extractive summariser  (🔴 high risk — drops whole sentences)
# ---------------------------------------------------------------------------

# A tiny stop-word list: extremely common words that carry little meaning, so
# they shouldn't count toward a sentence's "importance" score.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "to", "of", "in", "on", "for", "with", "as", "at", "by", "it",
    "this", "that", "these", "those", "i", "you", "he", "she", "we", "they",
    "do", "does", "did", "has", "have", "had", "will", "would", "can", "could",
    "not", "no", "so", "if", "then", "than", "from", "up", "out", "about",
}


def extractive_summary(text: str, keep_ratio: float = 0.6) -> str:
    """Keep only the most important sentences (opt-in, lossy).

    'Extractive' means we *select* existing sentences (never invent text) — this
    keeps it truthful and 100% free/offline. Importance = how many meaningful,
    frequent words a sentence contains. We keep ``keep_ratio`` of the sentences,
    in their original order.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= 1:
        return text.strip()

    # Count how often each meaningful word appears across the whole text.
    frequency: dict[str, int] = {}
    for sentence in sentences:
        for word in re.findall(r"[a-zA-Z']+", sentence.lower()):
            if word in _STOPWORDS:
                continue
            frequency[word] = frequency.get(word, 0) + 1

    def score(sentence: str) -> float:
        words = [w for w in re.findall(r"[a-zA-Z']+", sentence.lower()) if w not in _STOPWORDS]
        if not words:
            return 0.0
        # Average frequency of the sentence's meaningful words.
        return sum(frequency.get(w, 0) for w in words) / len(words)

    # How many sentences to keep (at least 1).
    keep_count = max(1, round(len(sentences) * keep_ratio))

    # Pick the highest-scoring sentence indices, then restore original order.
    ranked = sorted(range(len(sentences)), key=lambda i: score(sentences[i]), reverse=True)
    keep_indices = sorted(ranked[:keep_count])

    return " ".join(sentences[i] for i in keep_indices)


# ---------------------------------------------------------------------------
# 6. Caveman mode  (🟡 medium risk — tightens grammar but stays readable)
# ---------------------------------------------------------------------------

# The words we strip: articles carry almost no meaning, so dropping them keeps
# sentences perfectly understandable ("summarize the report" -> "summarize
# report"). We deliberately KEEP nouns, verbs, and pronouns so the result still
# reads as a real sentence rather than gibberish.
_CAVEMAN_DROP = {"a", "an", "the"}


def _capitalize_sentences(text: str) -> str:
    """Uppercase the first letter of the text and of each new sentence."""
    return re.sub(
        r"(^|[.!?]\s+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        text,
    )


def caveman(text: str) -> str:
    """'Caveman' style: drop articles and tighten, but keep readable sentences.

    Removes ``a`` / ``an`` / ``the`` (which add tokens but little meaning), tidies
    the leftover spacing/punctuation, then re-capitalizes each sentence so the
    output still looks like proper English — just leaner.
    """
    pattern = r"\b(?:" + "|".join(re.escape(w) for w in _CAVEMAN_DROP) + r")\b"
    text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean up the gaps the removals leave behind.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = _tidy_punctuation(text)
    text = normalize_whitespace(text)

    return _capitalize_sentences(text)


# ---------------------------------------------------------------------------
# 7. Number words -> digits  (🟡 medium risk — "fifty" -> "50" can shift tone)
# ---------------------------------------------------------------------------

_NUM_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_NUM_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_NUM_SCALES = {"hundred": 100, "thousand": 1000, "million": 1000000, "billion": 1000000000}
_NUM_WORDS = set(_NUM_UNITS) | set(_NUM_TENS) | set(_NUM_SCALES)

# One number "run": a number word, then more number words joined by spaces,
# hyphens, or "and" (as in "one hundred and twenty").
_NUM_ALT = "|".join(re.escape(w) for w in sorted(_NUM_WORDS, key=len, reverse=True))
_NUM_RUN_RE = re.compile(
    rf"\b(?:{_NUM_ALT})(?:[\s-]+(?:and[\s-]+)?(?:{_NUM_ALT}))*\b",
    flags=re.IGNORECASE,
)


def _run_to_int(words: list[str]) -> int:
    """Turn a list of number words (e.g. ['one','hundred','twenty']) into an int."""
    total = 0
    current = 0
    for word in words:
        if word in _NUM_UNITS:
            current += _NUM_UNITS[word]
        elif word in _NUM_TENS:
            current += _NUM_TENS[word]
        elif word == "hundred":
            current = (current or 1) * 100
        else:  # thousand / million / billion
            total += (current or 1) * _NUM_SCALES[word]
            current = 0
    return total + current


def numbers_to_digits(text: str) -> str:
    """Convert spelled-out numbers to digits, e.g. "one hundred" -> "100" (opt-in).

    Saves a token or two on written-out numbers. It can subtly change tone
    (formal prose often prefers words), so it's aggressive/opt-in.
    """

    def _replace(match: re.Match) -> str:
        words = [w.lower() for w in re.findall(r"[a-zA-Z]+", match.group(0))]
        words = [w for w in words if w != "and"]
        if not words:
            return match.group(0)
        return str(_run_to_int(words))

    return _NUM_RUN_RE.sub(_replace, text)
