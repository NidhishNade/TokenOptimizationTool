# Architecture

Token Optimizer measures and reduces the number of **tokens** in an LLM prompt
(a token ≈ ¾ of a word — the unit models read and bill by). It does this locally,
for free, with **no AI, no API keys, and no network calls** — just deterministic,
tokenizer-verified text rules. Paste text in, get a receipt out: tokens
before → after, percent saved, and estimated dollars saved.

---

## Summary

The design is **cleanly layered** — each layer only knows about the one below it:

```
        app.py  (Streamlit web UI)  ── or ──  cli.py  (terminal)
                            │
                            ▼
                        engine.py          run reducers in order, measure each step
                       /         \
              reducers.py       counter.py       the rules          the tokenizer (tiktoken)
                                    │
                                pricing.py        token count → USD estimate
```

The key architectural decision: **the engine is pure Python with zero UI
dependency.** The optimization "brain" is written once, and two different
front-ends (a web app and a command-line tool) plug into it. One source of
truth, no duplicated logic.

---

## Layers

### 1. Measuring — `counter.py` + `pricing.py`

- `count_tokens()` uses **`tiktoken`** (OpenAI's real tokenizer, `cl100k_base`
  encoding) to count tokens exactly the way a model would. Runs fully **offline**.
  The encoder is cached per encoding name so it isn't rebuilt on every call.
- `measure()` returns a `Measurement` dataclass (tokens, characters, words, cost).
- `pricing.py` is a static lookup table of **USD per 1,000,000 tokens** per model
  (gpt-4o-mini, gpt-4o, claude-haiku/sonnet/opus). It converts a token count into
  a dollar estimate. This is local math only — **not** a live pricing service.

### 2. Reducing — `reducers.py`

The heart of the tool. Every reducer has the same tiny shape:

```python
def some_reducer(text: str) -> str:
    ...  # return a smaller (or equal) version of the text
```

That uniform `text -> text` contract is *why* reducers are trivially unit-testable
and safe to chain in any order. They are split into two tiers:

**Safe — meaning-preserving, run by default:**

| Reducer | What it does |
|---|---|
| `remove_duplicate_blocks` | Drops whole paragraphs/blocks pasted more than once (100% safe; the big win on repetitive prompts) |
| `remove_duplicate_sentences` | Drops word-for-word repeated sentences |
| `simplify_phrases` | Swaps ~55 wordy phrases for shorter exact equivalents ("in order to" → "to") — every swap tokenizer-verified to actually reduce tokens |
| `remove_filler` | Removes politeness/padding ("please", "kindly", "very") and tidies leftover punctuation |
| `normalize_whitespace` | Collapses redundant spaces and blank lines |

**Aggressive — higher savings, can shift meaning, strictly opt-in:**

| Reducer | What it does |
|---|---|
| `numbers_to_digits` | "one hundred" → "100" |
| `abbreviate` | Shorthand swaps (only ones that don't increase tokens) |
| `caveman` | Drops articles (a/an/the), keeps readable sentences |
| `extractive_summary` | Keeps the highest-scoring sentences (lossy; never invents text) |

### 3. Orchestrating — `engine.py`

`optimize()` runs the pipeline and — crucially — **re-counts tokens after every
single reducer**. So the result is not a black box; it's a line-by-line receipt of
which rule saved what.

- `SAFE_PIPELINE` runs by default. `aggressive=True` and/or `caveman=True` append
  the opt-in steps. A fully custom `pipeline` can be passed in.
- Returns an `OptimizationResult` with per-step `Step` records and derived
  properties: `original_tokens`, `final_tokens`, `tokens_saved`, `percent_saved`,
  `cost_saved_usd`, plus a human-readable `summary()`.

### 4. Front-ends — `app.py` (Streamlit) + `cli.py` (argparse)

Both are thin layers over `engine.optimize()`:

- **CLI** — reads a file or stdin, supports `--aggressive`, `--caveman`,
  `--measure-only`, `--advise`, `--output`, `--model`; prints the optimized text to
  stdout and the report to stderr so text can be piped onward.
- **Web** — paste box, before/after/saved metrics, one-tap example chips, and a
  "Max savings" mode. Deployed free on Streamlit Community Cloud.

### Supporting modules

- `advisor.py` — structural suggestions (e.g. "this block repeats 3× — cache it").
- `analytics.py` — in-app `UsageStats` (runs, tokens saved, cost saved), shared
  across sessions via `st.cache_resource`. Local only; resets on restart.
- `local_llm.py` — **optional** offline compression via a local `gpt4all` model.
  Only used if explicitly requested and the package is installed; the hosted app
  falls back cleanly to the rule-based pipeline.

---

## Design principles

- **Measure, don't assume.** Every rule was validated against the real tokenizer
  before shipping. "Obvious" tricks that actually *increased* tokens (contractions,
  `with` → `w/`) were rejected.
- **Composable pure functions.** One job each, no shared state → testable in
  isolation, safe to reorder.
- **Safe by default, powerful by choice.** Meaning-preserving rules run
  automatically; anything lossy is opt-in.
- **Deterministic.** Same input always produces the same output — reproducible in
  a way a stochastic LLM can't be.
- **Invariant-tested.** 90+ tests, including a guardrail test that fails if any
  phrase-swap rule ever increases the token count.
- **Private by design.** No API keys, no outbound network calls, no secrets in the
  repo — so the tool literally cannot incur a charge, and nothing leaves the
  machine.

---

## Tech stack (all free / open-source)

| Tool | Role | Required? |
|---|---|---|
| **Python** (3.9+) | Core language | **Required** |
| **tiktoken** | Exact, offline token counting (`cl100k_base` encoding) | **Required** |
| **argparse** | Terminal CLI (stdlib) | **Required** (built in) |
| **dataclasses** | Typed result/report objects (stdlib) | **Required** (built in) |
| **pytest** | 90+ tests, including token-invariant guardrails | Optional (`[dev]`) |
| **Streamlit** | Pure-Python web UI | Optional (`[ui]`) |
| **gpt4all** | Offline local-LLM compression (no API, no keys) | Optional (`[llm]`) |
| **Streamlit Community Cloud** | Free hosting for the live app | Deploy only |
| **TOML** (`pyproject.toml`) | Packaging, CLI entry point, optional dependency groups | Build config |
| **Git + GitHub** | Version control, semver-tagged releases, MIT license | Project infra |

The only hard runtime dependency is **tiktoken** — everything the core tool does
(counting, reducing, pricing) runs on the Python standard library plus tiktoken.
The web UI, tests, and local-LLM features are opt-in extras.

### Why these choices

- **Python** — fast to iterate, and the natural home for `tiktoken`.
- **tiktoken over a hand-rolled counter** — it tokenizes the exact way the model
  does, so "before vs after" numbers are trustworthy, not approximations.
- **Streamlit over a JS frontend** — a working web UI in pure Python, no separate
  frontend stack, framework, or build step to maintain.
- **gpt4all (optional) over a paid API** — offline, free, and keeps the "no keys,
  nothing sent to a provider" guarantee intact even for the LLM feature.
- **TOML / pyproject.toml** — one standard file defines the package, the
  `token-optimizer` console command, and optional dependency groups (`[dev]`,
  `[ui]`, `[llm]`) so users install only what they need. The project uses a `src/`
  layout so tests import the installed package, not loose files.
