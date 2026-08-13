"""Tests for the local-LLM (gpt4all) compression module.

We never download or run a real model — we replace the model loader with a fake,
so the tests stay fast, offline, and deterministic.
"""

import pytest

import optimizer.local_llm as mod
from optimizer.local_llm import LocalLLMError, is_available, llm_compress


class _FakeSession:
    """Context manager standing in for gpt4all's chat_session()."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeModel:
    """Stand-in for a gpt4all model: returns a canned string from generate()."""

    def __init__(self, reply):
        self._reply = reply

    def chat_session(self):
        return _FakeSession()

    def generate(self, prompt, max_tokens=None):
        return self._reply


def test_is_available_true_when_installed():
    # gpt4all is installed in this environment.
    assert is_available() is True


def test_llm_compress_returns_stripped_text(monkeypatch):
    monkeypatch.setattr(mod, "_load_model", lambda *a, **k: _FakeModel("  short text  "))
    assert llm_compress("a long original prompt") == "short text"


def test_llm_compress_empty_response_raises(monkeypatch):
    monkeypatch.setattr(mod, "_load_model", lambda *a, **k: _FakeModel("   "))
    with pytest.raises(LocalLLMError, match="empty"):
        llm_compress("text")


def test_llm_compress_strips_chatty_preamble(monkeypatch):
    reply = "Sure! Here is the compressed text:\n\nSummarize report, list risks."
    monkeypatch.setattr(mod, "_load_model", lambda *a, **k: _FakeModel(reply))
    assert llm_compress("text") == "Summarize report, list risks."


def test_llm_compress_strips_surrounding_quotes(monkeypatch):
    monkeypatch.setattr(mod, "_load_model", lambda *a, **k: _FakeModel('"tight text"'))
    assert llm_compress("text") == "tight text"


def test_strip_preamble_keeps_plain_text():
    # No lead-in, no quotes — unchanged.
    assert mod._strip_preamble("just the answer") == "just the answer"


def test_llm_compress_load_failure_raises(monkeypatch):
    def boom(*a, **k):
        raise LocalLLMError("Could not load model 'ghost.gguf'")

    monkeypatch.setattr(mod, "_load_model", boom)
    with pytest.raises(LocalLLMError, match="Could not load"):
        llm_compress("text", model="ghost.gguf")


def test_llm_compress_generate_failure_raises(monkeypatch):
    class _Broken:
        def generate(self, prompt, max_tokens=None):
            raise ValueError("backend crashed")

    monkeypatch.setattr(mod, "_load_model", lambda *a, **k: _Broken())
    with pytest.raises(LocalLLMError, match="failed to generate"):
        llm_compress("text")
