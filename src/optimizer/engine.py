"""
The optimization engine: run the reducers in sequence and report the savings.

It measures the token count *after every reducer* so you can see which one saved
what — turning a black box into a clear, line-by-line receipt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import pricing, reducers
from .counter import count_tokens, estimate_cost

# A reducer is any function: text in, (smaller) text out.
Reducer = Callable[[str], str]

# The default pipeline, applied in this order. Each entry is (name, description,
# function). Whitespace runs last as a final tidy-up.
DEFAULT_PIPELINE: list[tuple[str, str, Reducer]] = [
    ("remove_duplicates", "Drop word-for-word repeated sentences", reducers.remove_duplicate_sentences),
    ("remove_filler", "Remove politeness / padding words", reducers.remove_filler),
    ("normalize_whitespace", "Collapse wasteful whitespace", reducers.normalize_whitespace),
]


@dataclass
class Step:
    """One reducer's contribution to the total savings."""

    name: str
    description: str
    tokens_before: int
    tokens_after: int

    @property
    def tokens_saved(self) -> int:
        return self.tokens_before - self.tokens_after


@dataclass
class OptimizationResult:
    """The full before/after report."""

    original_text: str
    optimized_text: str
    model: str
    steps: list[Step] = field(default_factory=list)

    @property
    def original_tokens(self) -> int:
        return self.steps[0].tokens_before if self.steps else count_tokens(self.original_text)

    @property
    def final_tokens(self) -> int:
        return self.steps[-1].tokens_after if self.steps else count_tokens(self.optimized_text)

    @property
    def tokens_saved(self) -> int:
        return self.original_tokens - self.final_tokens

    @property
    def percent_saved(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return self.tokens_saved / self.original_tokens * 100

    @property
    def cost_saved_usd(self) -> float:
        return estimate_cost(self.tokens_saved, self.model)

    def summary(self) -> str:
        """A human-readable multi-line report."""
        lines = [
            f"Original:  {self.original_tokens:,} tokens",
            f"Optimized: {self.final_tokens:,} tokens",
            f"Saved:     {self.tokens_saved:,} tokens ({self.percent_saved:.1f}%)"
            f"  ≈ ${self.cost_saved_usd:.6f} on {self.model}",
            "",
            "Per-step breakdown:",
        ]
        for step in self.steps:
            lines.append(
                f"  - {step.description}: "
                f"{step.tokens_before:,} → {step.tokens_after:,} "
                f"(-{step.tokens_saved:,})"
            )
        return "\n".join(lines)


def optimize(
    text: str,
    model: str = pricing.DEFAULT_MODEL,
    pipeline: list[tuple[str, str, Reducer]] | None = None,
) -> OptimizationResult:
    """Run the reducer pipeline over ``text`` and return a full report."""
    if pipeline is None:
        pipeline = DEFAULT_PIPELINE

    current = text
    tokens_before = count_tokens(current)
    steps: list[Step] = []

    for name, description, reducer in pipeline:
        reduced = reducer(current)
        tokens_after = count_tokens(reduced)
        steps.append(
            Step(
                name=name,
                description=description,
                tokens_before=tokens_before,
                tokens_after=tokens_after,
            )
        )
        current = reduced
        tokens_before = tokens_after

    return OptimizationResult(
        original_text=text,
        optimized_text=current,
        model=model,
        steps=steps,
    )
