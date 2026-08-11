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
- [ ] Phase 1 — Measure (token counter + cost)
- [ ] Phase 2 — Reduce engine (core)
- [ ] Phase 3 — Reduce advanced
- [ ] Phase 4 — CLI polish
- [ ] Phase 5 — Streamlit web UI
- [ ] Phase 6 — Visuals + extras

## Getting started

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the tests
pytest
```

## License

MIT
