"""Tests for the individual reducers."""

from optimizer import (
    normalize_whitespace,
    remove_duplicate_sentences,
    remove_filler,
)


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("hello      world") == "hello world"

    def test_strips_trailing_spaces_per_line(self):
        assert normalize_whitespace("hello   \nworld   ") == "hello\nworld"

    def test_collapses_many_blank_lines(self):
        assert normalize_whitespace("a\n\n\n\n\nb") == "a\n\nb"

    def test_trims_whole_text(self):
        assert normalize_whitespace("   hi   ") == "hi"

    def test_leaves_clean_text_untouched(self):
        assert normalize_whitespace("clean text") == "clean text"


class TestRemoveFiller:
    def test_removes_please(self):
        assert "please" not in remove_filler("Please summarize this").lower()

    def test_removes_polite_phrase(self):
        result = remove_filler("Summarize this, thank you so much").lower()
        assert "thank you" not in result

    def test_keeps_core_instruction(self):
        result = remove_filler("Please kindly summarize the report").lower()
        assert "summarize" in result
        assert "report" in result

    def test_word_boundary_protects_real_words(self):
        # "just" is filler, but "adjust" must survive.
        assert "adjust" in remove_filler("adjust the settings").lower()

    def test_no_leftover_double_spaces(self):
        assert "  " not in remove_filler("please   summarize really now")


class TestRemoveDuplicateSentences:
    def test_removes_exact_repeat(self):
        text = "Do the task. Do the task."
        assert remove_duplicate_sentences(text) == "Do the task."

    def test_keeps_distinct_sentences(self):
        text = "First point. Second point."
        assert remove_duplicate_sentences(text) == "First point. Second point."

    def test_ignores_case_when_deduping(self):
        text = "Repeat this. REPEAT THIS."
        # Only one survives.
        assert remove_duplicate_sentences(text).lower().count("repeat this") == 1

    def test_empty_text(self):
        assert remove_duplicate_sentences("") == ""
