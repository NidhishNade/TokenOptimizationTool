"""Token Optimizer — measure and reduce tokens in LLM prompts."""

from .advisor import Suggestion, advise, find_repeated_blocks
from .counter import Measurement, count_tokens, estimate_cost, measure
from .engine import OptimizationResult, Step, optimize
from .local_llm import LocalLLMError, is_available, llm_compress
from .reducers import (
    abbreviate,
    caveman,
    extractive_summary,
    normalize_whitespace,
    remove_duplicate_sentences,
    remove_filler,
)

__version__ = "1.2.3"

__all__ = [
    # measuring (Phase 1)
    "Measurement",
    "count_tokens",
    "estimate_cost",
    "measure",
    # reducing — safe (Phase 2)
    "OptimizationResult",
    "Step",
    "optimize",
    "normalize_whitespace",
    "remove_duplicate_sentences",
    "remove_filler",
    # reducing — advanced / opt-in (Phase 3+)
    "abbreviate",
    "caveman",
    "extractive_summary",
    # advice (Phase 3)
    "Suggestion",
    "advise",
    "find_repeated_blocks",
    # local LLM compression (opt-in)
    "LocalLLMError",
    "is_available",
    "llm_compress",
    "__version__",
]
