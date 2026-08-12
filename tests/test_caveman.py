"""Tests for caveman mode (readable article-stripping)."""

from optimizer import caveman, optimize, count_tokens


class TestCavemanReducer:
    def test_drops_articles(self):
        result = caveman("Summarize the report and read a book from an author.")
        lowered = result.lower()
        # No standalone articles should remain.
        assert " the " not in f" {lowered} "
        assert " a " not in f" {lowered} "
        assert " an " not in f" {lowered} "

    def test_keeps_meaningful_words(self):
        result = caveman("Summarize the quarterly report now.").lower()
        assert "summarize" in result
        assert "quarterly" in result
        assert "report" in result

    def test_word_boundary_protects_substrings(self):
        # "the" inside "theory" and "an" inside "analysis" must survive.
        result = caveman("The theory needs an analysis.").lower()
        assert "theory" in result
        assert "analysis" in result

    def test_recapitalizes_sentences(self):
        # After dropping "The", the sentence should still start with a capital.
        result = caveman("The report is ready. The team agreed.")
        assert result[0].isupper()

    def test_reduces_tokens(self):
        text = "The manager reviewed the report and the summary of the project."
        assert count_tokens(caveman(text)) < count_tokens(text)

    def test_single_sentence_still_reads(self):
        assert caveman("The cat sat on the mat.") == "Cat sat on mat."


class TestCavemanInEngine:
    def test_caveman_flag_saves_tokens(self):
        text = "Please summarize the report and focus on the key findings of the study."
        safe = optimize(text).final_tokens
        cave = optimize(text, caveman=True).final_tokens
        assert cave <= safe

    def test_caveman_off_by_default(self):
        text = "Summarize the report."
        # Default run should keep "the".
        assert "the" in optimize(text).optimized_text.lower()

    def test_caveman_and_aggressive_combine(self):
        text = "Please review the documentation because you are the owner of the app."
        result = optimize(text, caveman=True, aggressive=True)
        assert result.final_tokens < optimize(text).final_tokens
