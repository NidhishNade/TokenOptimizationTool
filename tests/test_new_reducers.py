"""Tests for the newer reducers: simplify_phrases and numbers_to_digits."""

from optimizer import (
    count_tokens,
    numbers_to_digits,
    optimize,
    remove_duplicate_blocks,
    simplify_phrases,
)


class TestRemoveDuplicateBlocks:
    def test_drops_exact_repeated_block(self):
        block = "You are a helpful analyst. Cite every source."
        text = f"{block}\n\nTask A.\n\n{block}\n\nTask B."
        out = remove_duplicate_blocks(text)
        assert out.count("You are a helpful analyst") == 1
        assert "Task A." in out and "Task B." in out

    def test_ignores_case_and_whitespace(self):
        text = "Follow   the guide.\n\nDo it.\n\nfollow the guide.\n\nDo it two."
        out = remove_duplicate_blocks(text)
        # The case/space variant of the guide block collapses to one occurrence
        # (kept block keeps its original spacing, so match on the word "guide").
        assert out.lower().count("guide") == 1

    def test_keeps_unique_blocks(self):
        text = "Block one.\n\nBlock two.\n\nBlock three."
        assert remove_duplicate_blocks(text) == text

    def test_big_savings_on_repetitive_prompt(self):
        block = "Context paragraph with several meaningful words repeated here."
        text = "\n\n".join([f"{block}\n\nQ{i}?" for i in range(6)])
        result = optimize(text)  # safe mode
        assert result.percent_saved > 50  # redundant blocks removed, meaning kept

    def test_in_default_pipeline(self):
        block = "Same instruction block here."
        text = f"{block}\n\nfirst.\n\n{block}\n\nsecond."
        out = optimize(text).optimized_text
        assert out.lower().count("same instruction block") == 1


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
