"""Tests for the Phase 3 advanced reducers and the advisor."""

from optimizer import (
    abbreviate,
    advise,
    extractive_summary,
    find_repeated_blocks,
    optimize,
    count_tokens,
)


class TestAbbreviate:
    def test_shortens_known_word(self):
        assert "bc" in abbreviate("I skipped it because of time").lower()

    def test_shortens_phrase(self):
        assert "ASAP" in abbreviate("Send it as soon as possible")

    def test_word_boundary_protects_substrings(self):
        # "and" -> "&", but "understand" must survive.
        assert "understand" in abbreviate("I understand the plan")

    def test_reduces_token_count(self):
        text = "Please send the documentation as soon as possible because you are late"
        assert count_tokens(abbreviate(text)) <= count_tokens(text)


class TestExtractiveSummary:
    def test_single_sentence_unchanged(self):
        assert extractive_summary("Only one sentence here.") == "Only one sentence here."

    def test_drops_sentences(self):
        text = (
            "The budget report shows revenue growth. "
            "Revenue grew across every region this quarter. "
            "The cafeteria now serves tacos on Fridays."
        )
        summary = extractive_summary(text, keep_ratio=0.5)
        # Fewer sentences than the original.
        assert summary.count(".") < text.count(".")

    def test_keeps_original_order(self):
        text = "Alpha topic sentence. Beta topic sentence. Gamma topic sentence."
        summary = extractive_summary(text, keep_ratio=1.0)
        assert summary.index("Alpha") < summary.index("Gamma")

    def test_never_invents_text(self):
        text = "Cats sleep a lot. Dogs run fast."
        summary = extractive_summary(text, keep_ratio=0.5)
        # Whatever survives must be an exact substring of the original.
        for sentence in summary.split(". "):
            assert sentence.strip(". ") in text


class TestAggressivePipeline:
    def test_aggressive_saves_at_least_as_much(self):
        text = "Please summarize the documentation because you are busy, thank you so much."
        safe = optimize(text, aggressive=False).final_tokens
        aggr = optimize(text, aggressive=True).final_tokens
        assert aggr <= safe

    def test_safe_is_still_default(self):
        text = "Please review this because you are the owner."
        # Default (no aggressive) should NOT abbreviate "because" -> "bc".
        assert "bc" not in optimize(text).optimized_text.lower().split()


class TestAdvisor:
    def test_detects_repeated_block(self):
        block = "This is a fairly long shared instruction block that repeats verbatim."
        text = f"{block}\n\nSome unique middle text here.\n\n{block}"
        suggestions = find_repeated_blocks(text, min_tokens=5)
        assert any(s.kind == "repeated-block" for s in suggestions)

    def test_no_false_positive_on_unique_text(self):
        text = "First unique paragraph.\n\nSecond different paragraph."
        assert advise(text) == []
