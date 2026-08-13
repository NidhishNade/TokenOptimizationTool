"""Run local LLM compression on the already-downloaded model (offline)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from optimizer import count_tokens, optimize  # noqa: E402
from optimizer.local_llm import llm_compress  # noqa: E402

prompt = (
    "I was hoping that maybe you could take a little bit of time to go ahead and "
    "carefully read through the rather long document that I have attached here, "
    "and then, once you have done that, could you please put together for me a "
    "reasonably short and easy to understand summary that basically explains what "
    "the document is mostly about, what the main points and takeaways are, and "
    "also whether there is anything in there that I really need to be worried "
    "about or pay close attention to going forward."
)

print("ORIGINAL   :", count_tokens(prompt), "tok")
print(" ", prompt, "\n")

rule = optimize(prompt)
print("RULE-BASED :", rule.final_tokens, "tok",
      f"({rule.percent_saved:.0f}% saved)")
print(" ", rule.optimized_text, "\n")

print("Running local model (offline)…\n")
llm_out = llm_compress(prompt, allow_download=False)
llm_tokens = count_tokens(llm_out)
saved = count_tokens(prompt) - llm_tokens
pct = saved / count_tokens(prompt) * 100
print("LLM-COMPRESSED:", llm_tokens, "tok", f"({pct:.0f}% saved)")
print(" ", llm_out)
