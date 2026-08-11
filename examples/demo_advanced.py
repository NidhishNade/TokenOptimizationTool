"""Demo of Phase 3 advanced features. Run: python examples/demo_advanced.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import advise, count_tokens, extractive_summary, optimize  # noqa: E402

prompt = """Please could you kindly review the documentation as soon as possible
because you are the owner. It is important to note that the documentation covers
the whole application. The report shows revenue grew in every region. The office
cafeteria now serves tacos on Fridays. Thank you so much."""

print("ORIGINAL:", count_tokens(prompt), "tokens\n")

safe = optimize(prompt, model="claude-opus")
print(f"SAFE:       {safe.final_tokens} tokens ({safe.percent_saved:.0f}% saved)")

aggr = optimize(prompt, model="claude-opus", aggressive=True)
print(f"AGGRESSIVE: {aggr.final_tokens} tokens ({aggr.percent_saved:.0f}% saved)")
print("  ->", aggr.optimized_text)

summ = extractive_summary(prompt, keep_ratio=0.5)
print(f"\nSUMMARY (50%): {count_tokens(summ)} tokens")
print("  ->", summ)

# Advisor demo: a prompt with a big repeated instruction block.
repeated = "Follow the company style guide and cite every source you use in full."
doc = f"{repeated}\n\nAnalyse Q1 results.\n\n{repeated}\n\nAnalyse Q2 results.\n\n{repeated}"
print("\nADVISOR:")
for s in advise(doc, min_tokens=5):
    print("  -", s.message)
