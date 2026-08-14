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

# Custom logo (a compression badge). Used for the browser-tab favicon and,
# inline (resized), in the hero heading.
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.svg"
_logo_raw = LOGO_PATH.read_text(encoding="utf-8")
HERO_LOGO = _logo_raw.replace(
    'width="64" height="64"',
    'style="height:2.6rem;width:2.6rem;vertical-align:-0.55rem;margin-right:0.45rem"',
)

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


def fmt_usd(amount: float) -> str:
    """Format dollars with enough precision to never show a misleading '$0.0000'.

    Model prices are tiny per call (a fraction of a cent), so a fixed 4-decimal
    format rounds real savings to zero. This shows enough significant digits for
    small amounts and clean cents for larger ones.
    """
    a = abs(amount)
    if a == 0:
        return "$0"
    if a >= 0.01:
        return f"${amount:,.2f}"
    if a >= 0.0001:
        return f"${amount:.4f}"
    if a >= 0.000001:
        return f"${amount:.6f}"
    return f"${amount:.2e}"


def usd_md(amount: float) -> str:
    """Same as fmt_usd but safe inside Streamlit markdown.

    Streamlit renders ``$...$`` as LaTeX math, which silently eats the dollar
    signs and collapses the spaces. Escaping the ``$`` keeps it literal in
    st.caption / st.markdown / help text.
    """
    return fmt_usd(amount).replace("$", "\\$")


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Token Optimizer",
    page_icon=str(LOGO_PATH),
    layout="centered",
    # Start with the settings panel tucked away behind the top-left ›/hamburger
    # toggle — the app works on safe defaults, so most visitors never open it.
    initial_sidebar_state="collapsed",
    menu_items={"about": "Token Optimizer — measure and cut tokens in LLM prompts."},
)

# --- Styling ---------------------------------------------------------------
# Cohesive palette: indigo is the brand, emerald green means "savings".
INDIGO = "#818cf8"      # brand / accent (matches config.toml primaryColor)
INDIGO_DEEP = "#6366f1"
EMERALD = "#34d399"     # savings cue — used for the "Saved" metric & charts
CARD_BG = "rgba(255,255,255,0.03)"
CARD_BORDER = "rgba(255,255,255,0.09)"

st.markdown(
    f"""
    <style>
      /* Hide the Community Cloud "Fork" / Deploy / GitHub source chrome — but
         NOT the whole toolbar, which also holds the sidebar-expand arrow we need
         now that the settings panel starts collapsed. */
      [data-testid="stAppDeployButton"],
      [data-testid="stActionButtonIcon"],
      [data-testid="stMainMenu"],
      header [data-testid="stHeaderActionElements"],
      a[href*="github.com"][target="_blank"] {{ display: none !important; }}

      /* Keep the expand-settings arrow visible and give it an obvious pill. */
      [data-testid="stExpandSidebarButton"] {{ display: flex !important; }}

      /* Tighten the top padding the hidden header leaves behind. */
      .block-container {{ padding-top: 2.4rem; max-width: 780px; }}

      /* Hero. */
      .hero-title {{
        font-size: 2.7rem; font-weight: 800; letter-spacing: -0.025em;
        line-height: 1.1; margin: 0 0 0.4rem 0;
        background: linear-gradient(100deg, {INDIGO} 10%, {EMERALD} 90%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
      }}
      .hero-sub {{ font-size: 1.06rem; opacity: 0.72; margin: 0 0 0.25rem 0; line-height: 1.5; }}

      /* "How it works" pills. */
      .steps {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.85rem 0 0.25rem; }}
      .step {{
        font-size: 0.82rem; padding: 0.3rem 0.8rem; border-radius: 999px;
        background: rgba(129,140,248,0.13); color: {INDIGO};
        border: 1px solid rgba(129,140,248,0.28); font-weight: 500;
      }}

      /* Metric cards. */
      [data-testid="stMetric"] {{
        background: {CARD_BG};
        border: 1px solid {CARD_BORDER};
        padding: 0.9rem 1.1rem; border-radius: 16px;
      }}
      [data-testid="stMetricValue"] {{ font-weight: 700; font-size: 1.7rem; }}
      /* Let metric labels wrap instead of truncating with an ellipsis. */
      [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {{
        white-space: normal !important; overflow: visible !important;
        text-overflow: clip !important;
      }}
      /* The "Saved" delta glows emerald — the payoff colour. */
      [data-testid="stMetricDelta"] {{ color: {EMERALD} !important; }}
      [data-testid="stMetricDelta"] svg {{ display: none; }}

      /* Buttons: rounded, bold; example chips get a subtle indigo hover. */
      .stButton > button {{
        border-radius: 10px; font-weight: 600;
        border: 1px solid {CARD_BORDER}; transition: all 0.15s ease;
      }}
      .stButton > button:hover {{
        border-color: {INDIGO}; color: {INDIGO};
        transform: translateY(-1px);
      }}
      .stDownloadButton > button {{ border-radius: 10px; font-weight: 600; }}

      /* Section labels. */
      .section-label {{
        text-transform: uppercase; letter-spacing: 0.09em; font-size: 0.72rem;
        opacity: 0.55; font-weight: 700; margin: 0.6rem 0 0.2rem;
      }}

      /* Inputs & expanders: softer, rounded, consistent with the cards. */
      .stTextArea textarea {{ border-radius: 12px; }}
      [data-testid="stExpander"] {{ border-radius: 12px; }}
      /* Sidebar gets a hair more separation. */
      section[data-testid="stSidebar"] {{ border-right: 1px solid {CARD_BORDER}; }}

      /* The sidebar starts collapsed, so make its expand toggle obvious —
         the default arrow is easy to miss in dark mode. */
      [data-testid="stExpandSidebarButton"] {{
        background: rgba(129,140,248,0.16) !important;
        border: 1px solid rgba(129,140,248,0.5) !important;
        border-radius: 10px !important;
      }}
      [data-testid="stExpandSidebarButton"] button,
      [data-testid="stExpandSidebarButton"] svg {{
        color: {INDIGO} !important; fill: {INDIGO} !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Charts use the palette: indigo for the before/after bars, emerald for savings.
ACCENT = INDIGO

# --- Hero ------------------------------------------------------------------
st.markdown(f'<div class="hero-title">{HERO_LOGO}Token Optimizer</div>', unsafe_allow_html=True)
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
        "- **Repeated-block remover** — drops whole paragraphs pasted more than once "
        "(the big win for repetitive prompts — can save 70–90% with zero meaning loss).\n"
        "- **Whitespace cleanup** — collapses extra spaces and blank lines.\n"
        "- **Duplicate remover** — drops sentences repeated word-for-word.\n"
        "- **Filler remover** — cuts politeness/padding (*please, kindly, thank you so much*).\n"
        "- **Wordy-phrase simplifier** — swaps bloated phrases for exact shorter ones "
        "(*in order to → to*, *due to the fact that → because*) — 50+ verified pairs.\n\n"
        "**Optional — open ⚙️ Settings (the › arrow, top-left):**\n"
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
    m1.metric("Your prompt", f"{original_tokens:,} tok",
              help="Tokens in the text you pasted.")
    m2.metric("After optimizing", f"{final_tokens:,} tok",
              help="Tokens the model would actually receive.")
    m3.metric("Saved", f"{saved:,} tok", f"-{percent:.0f}%",
              help="Fewer tokens = lower cost and more room in the context window.")

    # Clear, plain-language headline of what happened.
    if saved > 0:
        st.success(
            f"✂️ Cut **{saved:,} tokens** — **{percent:.0f}% smaller** "
            f"(from {original_tokens:,} down to {final_tokens:,})."
        )
    else:
        st.info(
            "This text is already lean, so there's nothing safe to trim. Savings "
            "are highest on padded or repetitive prompts — tap an **example** "
            "above, or open **⚙️ Settings** (the › arrow, top-left) and turn on "
            "**🔥 Max savings**."
        )

    # Cost: one call is a fraction of a cent on cheap models, so show the saving
    # per 1,000 calls (a real, non-zero number) alongside the per-call figure.
    if saved > 0:
        per_1k = cost_saved * 1000
        st.caption(
            f"💰 Cost on **{model}**: {usd_md(original_cost)} → {usd_md(optimized_cost)} "
            f"per call · **{usd_md(per_1k)} saved per 1,000 calls** "
            f"({usd_md(cost_saved)} each). Small per call — real money at volume."
        )
    else:
        st.caption(f"💰 Cost on **{model}**: {usd_md(original_cost)} per call.")

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
        st.bar_chart(step_df, color=EMERALD)
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
    # One call saves a fraction of a cent, so the raw cumulative total renders as
    # unreadable scientific notation. Scale it to "per 1,000 runs" for a clean,
    # meaningful number; keep the raw actual in the tooltip.
    cost_per_1k_runs = (stats.total_cost_saved_usd / stats.runs * 1000) if stats.runs else 0.0
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Optimizations run", f"{stats.runs:,}")
    a2.metric("Total tokens saved", f"{stats.total_tokens_saved:,}")
    a3.metric("Average saved", f"{stats.average_percent_saved:.0f}%")
    a4.metric("Cost / 1K runs", fmt_usd(cost_per_1k_runs),
              help="Your average saving scaled to 1,000 runs — a readable figure, "
                   f"since one call is a fraction of a cent. Actual so far: "
                   f"{usd_md(stats.total_cost_saved_usd)}.")

    if len(stats.history) > 1:
        st.caption("Percent saved per run")
        st.line_chart(
            pd.DataFrame({"% saved": stats.history}),
            color=EMERALD,
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
