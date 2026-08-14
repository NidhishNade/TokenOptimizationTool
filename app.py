"""
Token Optimizer — web UI (Streamlit).

Run it with:
    streamlit run app.py

This is a thin UI layer: all the real work lives in the `optimizer` package.
The page lets you paste text, choose a model, and see the token savings.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the `optimizer` package importable without installing it — this lets the
# app run on hosts (e.g. Streamlit Community Cloud) that only `pip install
# -r requirements.txt` and don't build the package.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd
import streamlit as st

from optimizer import advise, count_tokens, extractive_summary, measure, optimize
from optimizer import pricing
from optimizer.analytics import UsageStats
from optimizer.local_llm import LocalLLMError, is_available, llm_compress


@st.cache_resource
def get_usage_stats() -> UsageStats:
    """One analytics accumulator shared across all sessions (resets on restart)."""
    return UsageStats()


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Token Optimizer",
    page_icon="✂️",
    layout="centered",
    menu_items={"about": "Token Optimizer — measure and cut tokens in LLM prompts."},
)

# --- Styling ---------------------------------------------------------------
# A small, tasteful stylesheet: hides the hosting chrome (Fork/GitHub badge),
# sets an accent colour, and gives the metrics / example chips a card-like feel.
ACCENT = "#6c5ce7"
st.markdown(
    f"""
    <style>
      /* Hide Streamlit Community Cloud "Fork" / GitHub source chrome. */
      [data-testid="stToolbar"],
      [data-testid="stAppDeployButton"],
      [data-testid="stActionButtonIcon"],
      .stAppToolbar,
      header [data-testid="stHeaderActionElements"],
      a[href*="github.com"][target="_blank"] {{ display: none !important; }}

      /* Tighten the top padding the hidden header leaves behind. */
      .block-container {{ padding-top: 2.5rem; max-width: 760px; }}

      /* Hero. */
      .hero-title {{
        font-size: 2.6rem; font-weight: 800; letter-spacing: -0.02em;
        line-height: 1.1; margin: 0 0 0.35rem 0;
        background: linear-gradient(90deg, {ACCENT}, #00b894);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
      }}
      .hero-sub {{ font-size: 1.05rem; opacity: 0.75; margin: 0 0 0.25rem 0; }}

      /* "How it works" pills. */
      .steps {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.75rem 0 0.25rem; }}
      .step {{
        font-size: 0.82rem; padding: 0.28rem 0.7rem; border-radius: 999px;
        background: rgba(108,92,231,0.12); color: inherit; opacity: 0.9;
        border: 1px solid rgba(108,92,231,0.25);
      }}

      /* Metric cards. */
      [data-testid="stMetric"] {{
        background: rgba(128,128,128,0.06);
        border: 1px solid rgba(128,128,128,0.15);
        padding: 0.85rem 1rem; border-radius: 14px;
      }}

      /* Primary buttons in the accent colour. */
      .stButton > button {{ border-radius: 10px; font-weight: 600; }}

      /* Section labels. */
      .section-label {{
        text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.72rem;
        opacity: 0.6; font-weight: 700; margin: 0.5rem 0 0.15rem;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Hero ------------------------------------------------------------------
st.markdown('<div class="hero-title">✂️ Token Optimizer</div>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Trim the wasted tokens out of your AI prompts — '
    'cheaper calls, faster replies, more room in the context window.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="steps">'
    '<span class="step">1 · Paste your prompt</span>'
    '<span class="step">2 · We measure &amp; trim it</span>'
    '<span class="step">3 · See what you saved</span>'
    "</div>",
    unsafe_allow_html=True,
)
st.write("")

with st.expander("ℹ️  What does each setting do?"):
    st.markdown(
        "**Always on — safe, never changes meaning:**\n"
        "- **Whitespace cleanup** — collapses extra spaces and blank lines.\n"
        "- **Duplicate remover** — drops sentences repeated word-for-word.\n"
        "- **Filler remover** — cuts politeness/padding (*please, kindly, thank you so much*).\n"
        "- **Wordy-phrase simplifier** — swaps bloated phrases for exact shorter ones "
        "(*in order to → to*, *due to the fact that → because*) — 50+ verified pairs.\n\n"
        "**Optional — in the sidebar:**\n"
        "- **Aggressive mode** — shorthand the model still understands "
        "(*you → u*, *documentation → docs*, *ten → 10*). Can shift tone.\n"
        "- **Caveman mode** — drops *a / an / the*; still reads fine.\n"
        "- **Extractive summary** — keeps only the most important sentences (drops content).\n"
        "- **🔥 Max savings** — turns on aggressive + caveman + all phrase swaps at once. "
        "The biggest cut that still **keeps every sentence and its meaning** — it does *not* "
        "drop content (turn on Extractive summary separately if you want that).\n\n"
        "Every rule was checked against the real tokenizer (**tiktoken**) and kept only "
        "if it *actually* reduces tokens — so the savings you see are honest, not guesses."
    )

# One-click example prompts, each showing off a different kind of waste.
PRESETS: dict[str, str] = {
    "🙇 Polite padding": (
        "Please could you kindly summarize the following report for me. "
        "It is important to note that I would like you to focus on the key findings. "
        "Please could you kindly summarize the following report for me. "
        "Thank you so much, I really appreciate it."
    ),
    "🗯️ Wordy phrases": (
        "In order to complete this as soon as possible, please review the "
        "documentation because you are the owner of the application. With respect "
        "to the number of issues, there are approximately ten that you must fix."
    ),
    "🔁 Repeated block": (
        "Follow the full company style guide and cite every source you use.\n\n"
        "Analyse the Q1 revenue results.\n\n"
        "Follow the full company style guide and cite every source you use.\n\n"
        "Analyse the Q2 revenue results.\n\n"
        "Follow the full company style guide and cite every source you use."
    ),
}

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    st.markdown('<p class="section-label">Cost estimate</p>', unsafe_allow_html=True)
    model = st.selectbox(
        "Model",
        options=sorted(pricing.PRICE_PER_MILLION_TOKENS),
        index=sorted(pricing.PRICE_PER_MILLION_TOKENS).index(pricing.DEFAULT_MODEL),
        label_visibility="collapsed",
    )

    st.markdown('<p class="section-label">Reduction strength</p>', unsafe_allow_html=True)
    max_mode = st.checkbox(
        "🔥 Max savings",
        help="Turn on every word-level reducer at once — aggressive shorthand, "
             "caveman, and all 50+ phrase swaps. Squeezes the most tokens while "
             "keeping every sentence, so the meaning stays intact. (It does NOT "
             "drop sentences — turn on Extractive summary separately for that.)",
    )
    if max_mode:
        st.caption("🔥 Max word-level trimming — every sentence kept, meaning intact.")

    # The individual checkboxes are pure UI. Max mode is OR-ed into the effective
    # flags at point of use, so it reliably forces every reducer on regardless of
    # each checkbox's own state (avoids Streamlit's value=/disabled= rerun quirks).
    _aggressive = st.checkbox(
        "Aggressive mode",
        help="Also apply opt-in shorthand (you→u, documentation→docs, "
             "spelled-out numbers→digits). Can change meaning.",
    )
    _caveman = st.checkbox(
        "Caveman mode",
        help="Drop articles (a/an/the) but keep readable sentences.",
    )

    st.markdown('<p class="section-label">Lossy options</p>', unsafe_allow_html=True)
    _summary = st.checkbox(
        "Extractive summary",
        help="Keep only the most important sentences. Lossy — drops content.",
    )

    # Effective flags actually passed to the pipeline. Max mode forces on the
    # word-level reducers (aggressive + caveman) because they keep every sentence
    # and only shorten wording. It deliberately does NOT force the extractive
    # summary, which drops whole sentences — that stays a separate opt-in so Max
    # squeezes hard without ever losing content.
    aggressive = _aggressive or max_mode
    caveman_mode = _caveman or max_mode
    use_summary = _summary

    keep_ratio = st.slider(
        "Keep how much?",
        min_value=0.2, max_value=1.0, value=0.6, step=0.1,
        disabled=not use_summary,
    )
    show_advice = st.checkbox("Show structural advice", value=True)

    # Local LLM compression only appears when gpt4all is actually installed
    # (i.e. a local power-user who ran `pip install .[llm]`). On the hosted app
    # it isn't installed, so this experimental, sometimes-rambly option stays
    # hidden — visitors only see the reliable rule-based features.
    if is_available():
        st.divider()
        use_llm = st.checkbox(
            "Local LLM compression (experimental)",
            help="Rewrite shorter with a free, offline gpt4all model on your own "
                 "machine. The small model can ramble or vary run-to-run — check "
                 "the output before using it.",
        )
        if use_llm:
            st.caption("First use downloads a ~0.8 GB model (once), then runs offline.")
    else:
        use_llm = False

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
if "text" not in st.session_state:
    st.session_state.text = ""

# Example chips: clicking one loads it straight into the box — no second step.
st.markdown('<p class="section-label">Try an example</p>', unsafe_allow_html=True)
chip_cols = st.columns(len(PRESETS) + 1)
for col, (label, sample) in zip(chip_cols, PRESETS.items()):
    if col.button(label, use_container_width=True):
        st.session_state.text = sample
        st.session_state.pop("_last_run_signature", None)
if chip_cols[-1].button("Clear", use_container_width=True):
    st.session_state.text = ""

text = st.text_area(
    "Your prompt / text",
    key="text",
    height=200,
    placeholder="Paste a prompt here — or tap an example above…",
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if text.strip():
    result = optimize(text, model=model, aggressive=aggressive, caveman=caveman_mode)

    optimized_text = result.optimized_text
    if use_summary:
        optimized_text = extractive_summary(optimized_text, keep_ratio=keep_ratio)

    if use_llm:
        try:
            with st.spinner("Compressing with local model (first run downloads it)…"):
                compressed = llm_compress(optimized_text)
            if count_tokens(compressed) < count_tokens(optimized_text):
                optimized_text = compressed
            else:
                st.info("Local model output wasn't smaller; kept the rule-based result.")
        except LocalLLMError as exc:
            st.warning(f"LLM compression skipped — {exc}")

    final_tokens = count_tokens(optimized_text)
    original_tokens = result.original_tokens
    saved = original_tokens - final_tokens
    percent = (saved / original_tokens * 100) if original_tokens else 0.0

    original_cost = measure(text, model=model).estimated_cost_usd
    optimized_cost = measure(optimized_text, model=model).estimated_cost_usd
    cost_saved = original_cost - optimized_cost

    # Record this run in the shared analytics — but only once per distinct
    # optimization. Streamlit reruns the whole script on every widget change, so
    # we fingerprint the inputs and skip re-recording an identical result.
    run_signature = (text, model, aggressive, caveman_mode, use_summary, keep_ratio, use_llm)
    if st.session_state.get("_last_run_signature") != run_signature:
        get_usage_stats().record(original_tokens, final_tokens, cost_saved)
        st.session_state["_last_run_signature"] = run_signature

    st.subheader("Results")
    m1, m2, m3 = st.columns(3)
    m1.metric("Original", f"{original_tokens:,}", help="Tokens before optimizing.")
    m2.metric("Optimized", f"{final_tokens:,}", help="Tokens after optimizing.")
    m3.metric(
        "Saved", f"{saved:,}", f"-{percent:.0f}%",
        help="Fewer tokens = lower cost and more context room.",
    )

    # Savings depend on how wasteful the input is — set expectations honestly.
    if percent < 5:
        st.info(
            "This text is already lean, so there's little to trim. Savings are "
            "highest on padded or repetitive prompts — tap an **example** above, "
            "or turn on **Caveman / Aggressive** mode in the sidebar."
        )

    st.caption(
        f"💰 Estimated cost on **{model}**: "
        f"${original_cost:.6f} → ${optimized_cost:.6f} per call "
        f"(saves ${cost_saved:.6f})"
    )

    # --- Visual: before vs after -----------------------------------------
    compare_df = pd.DataFrame(
        {"tokens": [original_tokens, final_tokens]},
        index=["Original", "Optimized"],
    )
    st.bar_chart(compare_df, color=ACCENT, horizontal=True)

    st.subheader("Optimized text")
    st.code(optimized_text, language=None)
    st.download_button(
        "⬇️ Download optimized text",
        data=optimized_text,
        file_name="optimized.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("🔬 Per-step breakdown"):
        # A small chart of how many tokens each reducer saved.
        step_df = pd.DataFrame(
            {"tokens saved": [s.tokens_saved for s in result.steps]},
            index=[s.description for s in result.steps],
        )
        st.bar_chart(step_df, color="#00b894")
        for step in result.steps:
            st.write(
                f"**{step.description}**: "
                f"{step.tokens_before:,} → {step.tokens_after:,} "
                f"(saved {step.tokens_saved:,})"
            )
        if use_summary:
            st.write(
                f"**Extractive summary (keep {keep_ratio:.0%})**: "
                f"{result.final_tokens:,} → {final_tokens:,}"
            )

    if show_advice:
        suggestions = advise(text)
        if suggestions:
            st.subheader("💡 Structural suggestions")
            for s in suggestions:
                st.info(s.message)
else:
    st.info("👆 Paste a prompt above (or tap an example) to see the savings.")

# ---------------------------------------------------------------------------
# Usage analytics — running totals across all runs since the app last restarted
# ---------------------------------------------------------------------------
stats = get_usage_stats()
st.divider()
st.subheader("📊 Token analytics")
if stats.runs == 0:
    st.caption("Run an optimization above and the totals will start filling in here.")
else:
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Optimizations run", f"{stats.runs:,}")
    a2.metric("Total tokens saved", f"{stats.total_tokens_saved:,}")
    a3.metric("Average saved", f"{stats.average_percent_saved:.0f}%")
    a4.metric("Est. cost saved", f"${stats.total_cost_saved_usd:.4f}")

    if len(stats.history) > 1:
        st.caption("Percent saved per run")
        st.line_chart(
            pd.DataFrame({"% saved": stats.history}),
            color="#00b894",
        )

    st.caption(
        f"Best single run: **{stats.best_percent_saved:.0f}%** saved · "
        "totals are shared across visitors and reset when the app restarts."
    )
    if st.button("Reset analytics"):
        stats.reset()
        st.session_state.pop("_last_run_signature", None)
        st.rerun()

st.divider()
st.caption("Built with Python · tiktoken · Streamlit — all local, no API keys, no data leaves the server.")
