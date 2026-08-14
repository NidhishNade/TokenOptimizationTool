# Token Optimizer

**🚀 Live demo: [nidhish-token-optimizer.streamlit.app](https://nidhish-token-optimizer.streamlit.app)**

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://nidhish-token-optimizer.streamlit.app)

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

## How much does it save?

**It depends entirely on how wasteful your input is** — this is by design:

- **Already-lean text → close to 0% saved.** There's nothing to cut, and a good
  optimizer shouldn't damage tight writing.
- **Bloated text (politeness, padding, repeated instructions) → 40–60%+ saved.**

The rule-based reducers only *delete* clearly-wasteful words, so they never invent
or distort meaning. For deeper savings on verbose-but-not-repetitive text, the
optional local-LLM mode can *rewrite* it shorter (see below).

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
- [x] Deployed live + in-app token analytics 📊
- [x] Wordy-phrase simplifier + number→digit rules (every rule tokenizer-verified) ✂️
- [x] Polished UI + one-click **🔥 Max savings** (stacks every reducer at once) 🎨
- [x] 50+ tokenizer-verified wordy-phrase swaps (~41% on prose, safe mode) + in-app settings guide 📖

## Getting started

```bash
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

# Install the tool (this also enables the `token-optimizer` command)
pip install -e .

# ...or install with dev + UI extras (pytest, streamlit)
pip install -e ".[dev,ui]"

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

# Caveman mode (drop articles a/an/the, keep readable sentences)
token-optimizer prompt.txt --caveman

# Local LLM compression (free, offline; first run downloads a ~0.8GB model)
token-optimizer prompt.txt --llm

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

### Deploy it free (Streamlit Community Cloud)

The web app is ready to host for free:

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **Create app** → pick this repo, branch `main`, main file `app.py`.
3. **Deploy** — it installs `requirements.txt` and gives you a public URL.

Local-LLM mode is disabled on the hosted version (gpt4all is too heavy for the
free host); all the rule-based features work.

## Local LLM compression (optional, ⚠️ experimental)

Rule-based reducers only *delete* words. To *rewrite* text shorter while keeping
meaning, the tool can use a small language model that runs **entirely on your
machine** via [gpt4all](https://github.com/nomic-ai/gpt4all) — free, offline, no
API key. Your text never leaves your computer.

> **Experimental — quality depends on model size.** The small default model
> (Llama-3.2-1B) compresses aggressively but doesn't always follow instructions
> cleanly: it may add a preamble or vary run-to-run, so **check its output**. A
> larger local model gives cleaner results at the cost of a bigger download.

```bash
pip install -e ".[llm]"   # installs gpt4all
token-optimizer prompt.txt --llm
```

The first run downloads a ~0.8 GB model file (once); after that it works offline.

## License

MIT
