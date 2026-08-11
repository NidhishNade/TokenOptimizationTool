"""Tests for the optimization engine."""

from optimizer import optimize, count_tokens


def test_optimize_reduces_or_keeps_tokens():
    text = "Please could you kindly summarize this report, thank you so much."
    result = optimize(text)
    assert result.final_tokens <= result.original_tokens


def test_optimize_actually_saves_on_padded_text():
    text = "Please please summarize.   Please please summarize."
    result = optimize(text)
    assert result.tokens_saved > 0
    assert result.percent_saved > 0


def test_result_has_a_step_per_reducer():
    result = optimize("Some text here.")
    # Default pipeline has 3 reducers.
    assert len(result.steps) == 3


def test_step_math_is_consistent():
    result = optimize("Please kindly do the thing. Please kindly do the thing.")
    # Each step's 'before' should equal the previous step's 'after'.
    for earlier, later in zip(result.steps, result.steps[1:]):
        assert earlier.tokens_after == later.tokens_before


def test_optimized_text_matches_reported_final_tokens():
    result = optimize("Please summarize.   Please summarize.")
    assert count_tokens(result.optimized_text) == result.final_tokens


def test_empty_text_is_safe():
    result = optimize("")
    assert result.tokens_saved == 0
    assert result.percent_saved == 0.0


def test_summary_mentions_savings():
    result = optimize("Please please summarize. Please please summarize.")
    assert "Saved" in result.summary()
