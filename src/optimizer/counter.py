"""
Measure text: how many tokens it uses and roughly what it costs.

A *token* is the unit LLMs read and bill by — very roughly 3/4 of a word.
We count tokens with `tiktoken` (OpenAI's tokenizer). It runs fully offline and
free. For Claude the count is a close approximation, which is fine for comparing
"before vs after" savings — the whole point of this tool.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from . import pricing

# tiktoken has several "encodings" (rulebooks for splitting text into tokens).
# cl100k_base is the one used by GPT-3.5/GPT-4 and is a solid general default.
DEFAULT_ENCODING = "cl100k_base"

# Caching the encoder avoids reloading it on every call (it's a little expensive
# to build). We keep one per encoding name.
_ENCODERS: dict[str, tiktoken.Encoding] = {}


def _get_encoder(encoding_name: str) -> tiktoken.Encoding:
    if encoding_name not in _ENCODERS:
        _ENCODERS[encoding_name] = tiktoken.get_encoding(encoding_name)
    return _ENCODERS[encoding_name]


def count_tokens(text: str, encoding_name: str = DEFAULT_ENCODING) -> int:
    """Return the number of tokens in ``text``."""
    encoder = _get_encoder(encoding_name)
    return len(encoder.encode(text))


def estimate_cost(token_count: int, model: str = pricing.DEFAULT_MODEL) -> float:
    """Estimate the USD cost of ``token_count`` tokens for a given model."""
    per_million = pricing.price_per_million(model)
    return token_count / 1_000_000 * per_million


@dataclass
class Measurement:
    """A small report describing a piece of text."""

    text: str
    tokens: int
    characters: int
    words: int
    model: str
    estimated_cost_usd: float

    def summary(self) -> str:
        """A one-line human-readable summary."""
        return (
            f"{self.tokens:,} tokens "
            f"({self.characters:,} chars, {self.words:,} words) "
            f"≈ ${self.estimated_cost_usd:.6f} on {self.model}"
        )


def measure(
    text: str,
    model: str = pricing.DEFAULT_MODEL,
    encoding_name: str = DEFAULT_ENCODING,
) -> Measurement:
    """Measure ``text`` and return a :class:`Measurement` report."""
    tokens = count_tokens(text, encoding_name)
    return Measurement(
        text=text,
        tokens=tokens,
        characters=len(text),
        words=len(text.split()),
        model=model,
        estimated_cost_usd=estimate_cost(tokens, model),
    )
