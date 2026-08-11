"""Token Optimizer — measure and reduce tokens in LLM prompts."""

from .counter import Measurement, count_tokens, estimate_cost, measure
from .engine import OptimizationResult, Step, optimize
from .reducers import (
    normalize_whitespace,
    remove_duplicate_sentences,
    remove_filler,
)

__version__ = "0.2.0"

__all__ = [
    # measuring (Phase 1)
    "Measurement",
    "count_tokens",
    "estimate_cost",
    "measure",
    # reducing (Phase 2)
    "OptimizationResult",
    "Step",
    "optimize",
    "normalize_whitespace",
    "remove_duplicate_sentences",
    "remove_filler",
    "__version__",
]
