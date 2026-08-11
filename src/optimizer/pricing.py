"""
Rough per-token prices for popular LLMs, used to estimate cost.

Prices are in **US dollars per 1,000,000 input tokens** and are approximate —
providers change them and charge different rates for input vs output. Treat these
as ballpark figures for comparison, and edit them anytime new prices come out.
"""

from __future__ import annotations

# model name  ->  USD per 1 million input tokens
PRICE_PER_MILLION_TOKENS: dict[str, float] = {
    "gpt-4o-mini": 0.15,
    "gpt-4o": 2.50,
    "claude-haiku": 0.80,
    "claude-sonnet": 3.00,
    "claude-opus": 15.00,
}

# Used when the caller doesn't name a model.
DEFAULT_MODEL = "gpt-4o-mini"


def price_per_million(model: str = DEFAULT_MODEL) -> float:
    """Return the USD-per-million-tokens price for a model.

    Raises a helpful error if the model isn't in the table, listing the ones we know.
    """
    try:
        return PRICE_PER_MILLION_TOKENS[model]
    except KeyError:
        known = ", ".join(sorted(PRICE_PER_MILLION_TOKENS))
        raise ValueError(
            f"Unknown model {model!r}. Known models: {known}. "
            f"Add it to PRICE_PER_MILLION_TOKENS in pricing.py."
        ) from None
