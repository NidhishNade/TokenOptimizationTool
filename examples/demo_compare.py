"""Show how savings depend on input and mode. Run: python examples/demo_compare.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import count_tokens, optimize  # noqa: E402


def show(label, text):
    orig = count_tokens(text)
    for name, kw in [
        ("safe", {}),
        ("caveman", {"caveman": True}),
        ("aggressive", {"aggressive": True}),
        ("caveman+aggressive", {"caveman": True, "aggressive": True}),
    ]:
        r = optimize(text, **kw)
        print(f"  {name:20} {orig:3} -> {r.final_tokens:3} tok  ({r.percent_saved:.0f}% saved)")
    print()


# 1. A LEAN prompt — little to cut.
lean = "Summarize this report and list the top three risks."
print(f"LEAN INPUT ({count_tokens(lean)} tok): {lean!r}")
show("lean", lean)

# 2. A BLOATED prompt — padding + a repeated instruction.
bloated = (
    "Please could you kindly summarize the following quarterly report for me. "
    "It is important to note that I would really like you to focus on the key "
    "findings and the main risks. Please could you kindly summarize the following "
    "quarterly report for me. Thank you so very much, I really appreciate it."
)
print(f"BLOATED INPUT ({count_tokens(bloated)} tok):")
show("bloated", bloated)
