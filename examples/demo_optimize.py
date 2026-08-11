"""Demo of the Phase 2 reduction engine. Run: python examples/demo_optimize.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import optimize  # noqa: E402

# A deliberately bloated prompt: politeness, padding, a repeated instruction,
# and messy whitespace — the kind of thing people actually paste into chatbots.
bloated = """Please could you kindly summarize the following report for me.

It is important to note that   I would like you to focus on the key findings.


Please could you kindly summarize the following report for me.

Thank you so much, I really appreciate it."""

result = optimize(bloated, model="claude-opus")

print("=== BEFORE ===")
print(repr(bloated))
print("\n=== AFTER ===")
print(repr(result.optimized_text))
print("\n=== REPORT ===")
print(result.summary())
