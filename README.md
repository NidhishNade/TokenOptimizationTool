# Token Optimizer

A free, open-source tool that measures and reduces the number of **tokens** in your
LLM prompts — so your calls to Claude / GPT are **cheaper, faster, and fit more in**.

Give it text, and it will:
1. **Measure** how many tokens it uses (and roughly what it costs).
2. **Reduce** those tokens using several safe techniques.
3. **Show** you the before/after savings.

> Think of it as a "minifier," but for LLM prompts instead of code.

## Why?

A **token** is roughly ¾ of a word. LLMs charge per token and limit how many fit in
one request. Saying the same thing in fewer tokens saves money and leaves more room
for real content.

## Tech stack (all free & permissively licensed)

- **Python 3** — the core engine
- **tiktoken** — accurate local token counting (no network, no cost)
- **pytest** — tests
- **Streamlit** *(later)* — pure-Python web UI

## Project status

Built in phases:

- [x] Phase 0 — Project setup
- [x] Phase 1 — Measure (token counter + cost)
- [x] Phase 2 — Reduce engine (core)
- [x] Phase 3 — Reduce advanced
- [x] Phase 4 — CLI polish
- [x] Phase 5 — Streamlit web UI
- [x] Phase 6 — Visuals + extras 🎉

## Getting started

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

# Install the tool (this also enables the `token-optimizer` command)
pip install -e .

# Run the tests
pytest
```

## Command-line usage

```bash
# Optimize a file and see the before/after report
token-optimizer prompt.txt

# Estimate cost for a specific model
token-optimizer prompt.txt --model claude-opus

# Aggressive mode (opt-in shorthand: "you" -> "u", "documentation" -> "docs")
token-optimizer prompt.txt --aggressive

# Save the shortened text to a file
token-optimizer prompt.txt --output short.txt

# Just measure, don't reduce
token-optimizer prompt.txt --measure-only

# Show structural advice (repeated blocks you could cache)
token-optimizer prompt.txt --advise

# Pipe text in from another command
echo "Please kindly summarize this, thank you so much." | token-optimizer
```

The optimized text is printed to **stdout** and the report to **stderr**, so you
can redirect just the text: `token-optimizer prompt.txt > short.txt`.

## Web app

A pure-Python web UI (Streamlit) — paste text, tweak settings, see the savings.

```bash
pip install -e ".[ui]"   # installs Streamlit
streamlit run app.py
```

Then open http://localhost:8501.

## License

MIT
