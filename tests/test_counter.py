"""Tests for the token counter and cost estimator."""

import pytest

from optimizer import count_tokens, estimate_cost, measure
from optimizer import pricing


def test_empty_text_has_zero_tokens():
    assert count_tokens("") == 0


def test_count_is_positive_for_real_text():
    assert count_tokens("Hello, world!") > 0


def test_longer_text_has_more_tokens():
    short = count_tokens("Hello")
    long = count_tokens("Hello there, how are you doing today?")
    assert long > short


def test_count_is_deterministic():
    text = "The quick brown fox jumps over the lazy dog."
    assert count_tokens(text) == count_tokens(text)


def test_estimate_cost_scales_with_tokens():
    one_million_cost = estimate_cost(1_000_000, "gpt-4o-mini")
    # gpt-4o-mini is $0.15 per million tokens.
    assert one_million_cost == pytest.approx(0.15)


def test_estimate_cost_zero_tokens_is_free():
    assert estimate_cost(0) == 0.0


def test_unknown_model_raises_helpful_error():
    with pytest.raises(ValueError, match="Unknown model"):
        pricing.price_per_million("gpt-9-ultra")


def test_measure_returns_consistent_report():
    result = measure("Hello, world!", model="gpt-4o-mini")
    assert result.tokens > 0
    assert result.characters == len("Hello, world!")
    assert result.words == 2
    assert result.estimated_cost_usd > 0
    # The summary should mention the token count.
    assert "tokens" in result.summary()
