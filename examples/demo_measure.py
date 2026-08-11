"""Quick demo of the Phase 1 token counter. Run: python examples/demo_measure.py"""

import sys
from pathlib import Path

# Let this script find the package under ../src without installing anything.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import measure  # noqa: E402

sample = (
    "Please could you kindly summarize the following document for me "
    "in a clear and concise way, thank you so much."
)

print(f"Text: {sample!r}\n")
for model in ["gpt-4o-mini", "claude-sonnet", "claude-opus"]:
    print(measure(sample, model=model).summary())
