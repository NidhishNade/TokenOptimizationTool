"""
Optional LLM-based compression using a **local, in-process** model (gpt4all).

Rule-based reducers can only delete words. To actually *rewrite* text shorter
while keeping meaning, you need a language model. This module runs a small model
locally via [gpt4all](https://github.com/nomic-ai/gpt4all):

- **Free** (MIT) and **offline** — your text never leaves the machine.
- **No API key, no server** — the model runs inside this Python process.
- The only network use is a **one-time** download of the model weights
  (~0.8 GB for the default 1B model) the first time you run it.

If gpt4all or the model isn't available, everything else in the tool still
works; this feature simply reports what to do.
"""

from __future__ import annotations

import functools

# A small, fast instruct model — plenty for "make this shorter".
DEFAULT_LLM_MODEL = "Llama-3.2-1B-Instruct-Q4_0.gguf"

# What we tell the local model. We ask for ONLY the compressed text so we don't
# have to strip chatty preambles.
_COMPRESS_PROMPT = (
    "You compress prompts. Rewrite the text below using as few words as possible "
    "while preserving every instruction and essential detail. Keep it clear and "
    "grammatical. Reply with ONLY the compressed text — no preamble, no quotes.\n\n"
    "TEXT:\n{text}"
)


class LocalLLMError(RuntimeError):
    """Raised when the local model can't be loaded or run."""


def is_available() -> bool:
    """Return True if the gpt4all library is importable (never raises)."""
    try:
        import gpt4all  # noqa: F401
        return True
    except ImportError:
        return False


@functools.lru_cache(maxsize=2)
def _load_model(model_name: str, allow_download: bool):
    """Load (and cache) a gpt4all model. Downloads weights on first use."""
    try:
        from gpt4all import GPT4All
    except ImportError as exc:
        raise LocalLLMError(
            "Local LLM compression needs gpt4all. Install it (free):\n"
            "  pip install gpt4all"
        ) from exc
    try:
        return GPT4All(model_name, allow_download=allow_download)
    except Exception as exc:  # gpt4all raises various errors for load/download
        raise LocalLLMError(
            f"Could not load model {model_name!r}: {exc}"
        ) from exc


def llm_compress(
    text: str,
    model: str = DEFAULT_LLM_MODEL,
    allow_download: bool = True,
    max_tokens: int | None = None,
) -> str:
    """Compress ``text`` with a local gpt4all model and return the shorter text.

    Raises :class:`LocalLLMError` if the library or model isn't available, so
    callers can fall back to the rule-based result. The first call may block
    while the model weights download (once).
    """
    llm = _load_model(model, allow_download)

    prompt = _COMPRESS_PROMPT.format(text=text)
    # Cap output near the input length — the result should be shorter anyway.
    cap = max_tokens or max(64, len(text.split()) + 32)
    try:
        output = llm.generate(prompt, max_tokens=cap)
    except Exception as exc:
        raise LocalLLMError(f"Local model failed to generate: {exc}") from exc

    compressed = (output or "").strip()
    if not compressed:
        raise LocalLLMError("Local model returned an empty response.")
    return compressed
