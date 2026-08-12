"""Demo of caveman mode. Run: python examples/demo_caveman.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import count_tokens, optimize  # noqa: E402

text = (
    "Please could you summarize the quarterly report for the board. "
    "The report should cover the revenue, the costs, and the key risks "
    "of the business over the last year."
)

print("ORIGINAL   :", count_tokens(text), "tok")
print(" ", text, "\n")

safe = optimize(text, model="claude-opus")
print("SAFE       :", safe.final_tokens, "tok")
print(" ", safe.optimized_text, "\n")

cave = optimize(text, model="claude-opus", caveman=True)
print("CAVEMAN    :", cave.final_tokens, f"tok  ({cave.percent_saved:.0f}% saved)")
print(" ", cave.optimized_text, "\n")

both = optimize(text, model="claude-opus", caveman=True, aggressive=True)
print("CAVEMAN+AGG:", both.final_tokens, f"tok  ({both.percent_saved:.0f}% saved)")
print(" ", both.optimized_text)
