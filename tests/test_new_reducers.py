"""Tests for the newer reducers: simplify_phrases and numbers_to_digits."""

from optimizer import (
    count_tokens,
    numbers_to_digits,
    optimize,
    simplify_phrases,
)


class TestSimplifyPhrases:
    def test_swaps_wordy_phrase(self):
        assert simplify_phrases("Do it in order to win") == "Do it to win"

    def test_because_swap(self):
        out = simplify_phrases("We paused due to the fact that it broke")
        assert "because" in out
        assert "due to the fact that" not in out

    def test_recapitalizes_sentence_start(self):
        # "In order to" at the start becomes "To" (capitalized), not "to".
        assert simplify_phrases("In order to win, prepare.").startswith("To win")

    def test_saves_tokens(self):
        text = "In order to proceed, with regard to the plan, a large number of steps remain."
        assert count_tokens(simplify_phrases(text)) < count_tokens(text)

    def test_is_in_default_pipeline(self):
        # simplify_phrases is safe, so it runs without aggressive=True.
        out = optimize("Do this in order to finish.").optimized_text
        assert "in order to" not in out.lower()

    def test_newly_added_pairs(self):
        # A spot-check of the expanded phrase list (mid-sentence to avoid the
        # sentence-start recapitalization).
        assert simplify_phrases("Do it as well as the rest") == "Do it and the rest"
        assert "consider" in simplify_phrases("please take into account the risk")
        assert "because" in simplify_phrases("we stopped for the reason that it broke")
        assert simplify_phrases("I know the fact that it works") == "I know that it works"

    def test_every_pair_reduces_or_holds_tokens(self):
        # Guardrail: no phrase in the table may INCREASE tokens in context.
        from optimizer.reducers import _WORDY_PHRASES
        for phrase, short in _WORDY_PHRASES.items():
            before = count_tokens(f"We did it {phrase} the team agreed.")
            after = count_tokens(f"We did it {short} the team agreed.")
            assert after <= before, f"{phrase!r} -> {short!r} increased tokens"


class TestNumbersToDigits:
    def test_simple_tens(self):
        assert numbers_to_digits("I have fifty apples") == "I have 50 apples"

    def test_compound(self):
        assert numbers_to_digits("twenty five people") == "25 people"

    def test_hundreds(self):
        assert numbers_to_digits("one hundred dollars") == "100 dollars"

    def test_hundred_with_and(self):
        assert numbers_to_digits("one hundred and twenty") == "120"

    def test_thousands(self):
        assert numbers_to_digits("three thousand") == "3000"

    def test_leaves_non_numbers_alone(self):
        assert numbers_to_digits("the quick brown fox") == "the quick brown fox"

    def test_only_in_aggressive_pipeline(self):
        text = "I counted fifty items"
        safe = optimize(text, aggressive=False).optimized_text
        aggr = optimize(text, aggressive=True).optimized_text
        assert "fifty" in safe          # untouched by default
        assert "50" in aggr             # converted when aggressive
