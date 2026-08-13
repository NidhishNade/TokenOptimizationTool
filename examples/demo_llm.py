"""
Demo of local LLM compression (gpt4all).

WARNING: the first run downloads a ~0.8 GB model file (once), then runs offline.
Run: python examples/demo_llm.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import count_tokens, optimize  # noqa: E402
from optimizer.local_llm import LocalLLMError, is_available, llm_compress  # noqa: E402

text = (
    "Please could you kindly go through the attached quarterly report and then "
    "write me a short summary that covers the revenue, the main costs, and any "
    "important risks that the business is currently facing this year."
)

print("Original :", count_tokens(text), "tok")
print(" ", text, "\n")

rule = optimize(text)
print("Rule-based:", rule.final_tokens, "tok")
print(" ", rule.optimized_text, "\n")

if not is_available():
    print("gpt4all not installed — run: pip install gpt4all")
    sys.exit(0)

try:
    print("Running local model (first run downloads ~0.8 GB)…")
    compressed = llm_compress(rule.optimized_text)
except LocalLLMError as exc:
    print("LLM step skipped:", exc)
else:
    print("LLM-compressed:", count_tokens(compressed), "tok")
    print(" ", compressed)
