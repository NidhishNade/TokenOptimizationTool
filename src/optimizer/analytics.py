"""In-app usage analytics for the token-optimization work.

This is a tiny, dependency-free accumulator. It does **not** phone home or use
any external service (no Google Analytics, no tracking scripts) — it just adds
up the token stats from each optimization run so the web UI can show totals like
"tokens saved so far" and "average % saved".

The web app keeps one shared instance in memory (via ``st.cache_resource``), so
the numbers aggregate across everyone using the app and reset when the server
restarts. That's intentional — see the app's analytics panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UsageStats:
    """Running totals across every optimization run since the last restart."""

    runs: int = 0
    total_original_tokens: int = 0
    total_final_tokens: int = 0
    total_tokens_saved: int = 0
    total_cost_saved_usd: float = 0.0
    best_percent_saved: float = 0.0
    # Percent saved for each run, in order — handy for a small trend chart.
    history: list[float] = field(default_factory=list)

    def record(
        self,
        original_tokens: int,
        final_tokens: int,
        cost_saved_usd: float = 0.0,
    ) -> float:
        """Add one optimization run and return its percent saved.

        ``final_tokens`` is clamped so it never exceeds ``original_tokens`` —
        an optimization should not report negative savings in the totals.
        """
        original_tokens = max(0, int(original_tokens))
        final_tokens = max(0, int(final_tokens))
        if final_tokens > original_tokens:
            final_tokens = original_tokens

        saved = original_tokens - final_tokens
        self.runs += 1
        self.total_original_tokens += original_tokens
        self.total_final_tokens += final_tokens
        self.total_tokens_saved += saved
        self.total_cost_saved_usd += max(0.0, float(cost_saved_usd))

        percent = (saved / original_tokens * 100) if original_tokens else 0.0
        self.best_percent_saved = max(self.best_percent_saved, percent)
        self.history.append(percent)
        return percent

    @property
    def average_percent_saved(self) -> float:
        """Overall % saved, weighted by token volume (not a mean of means)."""
        if self.total_original_tokens == 0:
            return 0.0
        return self.total_tokens_saved / self.total_original_tokens * 100

    def reset(self) -> None:
        """Clear all totals (used by tests and a manual reset button)."""
        self.runs = 0
        self.total_original_tokens = 0
        self.total_final_tokens = 0
        self.total_tokens_saved = 0
        self.total_cost_saved_usd = 0.0
        self.best_percent_saved = 0.0
        self.history.clear()
