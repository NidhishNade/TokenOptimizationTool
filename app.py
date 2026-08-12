"""
Token Optimizer — web UI (Streamlit).

Run it with:
    streamlit run app.py

This is a thin UI layer: all the real work lives in the `optimizer` package.
The page lets you paste text, choose a model, and see the token savings.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from optimizer import advise, count_tokens, extractive_summary, measure, optimize
from optimizer import pricing

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Token Optimizer", page_icon="✂️", layout="centered")

st.title("✂️ Token Optimizer")
st.caption(
    "Measure and reduce the tokens in your LLM prompts — cheaper, faster, "
    "and fits more in the context window."
)

# One-click example prompts, each showing off a different kind of waste.
PRESETS: dict[str, str] = {
    "Polite padding + a repeat": (
        "Please could you kindly summarize the following report for me. "
        "It is important to note that I would like you to focus on the key findings. "
        "Please could you kindly summarize the following report for me. "
        "Thank you so much, I really appreciate it."
    ),
    "Wordy phrases (aggressive shines)": (
        "In order to complete this as soon as possible, please review the "
        "documentation because you are the owner of the application. With respect "
        "to the number of issues, there are approximately ten that you must fix."
    ),
    "Repeated instruction block (advisor)": (
        "Follow the full company style guide and cite every source you use.\n\n"
        "Analyse the Q1 revenue results.\n\n"
        "Follow the full company style guide and cite every source you use.\n\n"
        "Analyse the Q2 revenue results.\n\n"
        "Follow the full company style guide and cite every source you use."
    ),
}
EXAMPLE = PRESETS["Polite padding + a repeat"]

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    model = st.selectbox(
        "Model (for cost estimate)",
        options=sorted(pricing.PRICE_PER_MILLION_TOKENS),
        index=sorted(pricing.PRICE_PER_MILLION_TOKENS).index(pricing.DEFAULT_MODEL),
    )
    aggressive = st.checkbox(
        "Aggressive mode",
        help="Also apply opt-in shorthand (you→u, documentation→docs). Can change meaning.",
    )
    caveman_mode = st.checkbox(
        "Caveman mode",
        help="Drop articles (a/an/the) but keep readable sentences.",
    )
    use_summary = st.checkbox(
        "Extractive summary",
        help="Keep only the most important sentences. Lossy — drops content.",
    )
    keep_ratio = st.slider(
        "Summary: keep how much?",
        min_value=0.2, max_value=1.0, value=0.6, step=0.1,
        disabled=not use_summary,
    )
    show_advice = st.checkbox("Show structural advice", value=True)

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
if "text" not in st.session_state:
    st.session_state.text = ""

col_preset, col_load, col_clear = st.columns([2, 1, 1])
chosen_preset = col_preset.selectbox("Examples", list(PRESETS), label_visibility="collapsed")
if col_load.button("Load", use_container_width=True):
    st.session_state.text = PRESETS[chosen_preset]
if col_clear.button("Clear", use_container_width=True):
    st.session_state.text = ""

text = st.text_area(
    "Your prompt / text",
    key="text",
    height=200,
    placeholder="Paste a prompt here…",
)

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if text.strip():
    result = optimize(text, model=model, aggressive=aggressive, caveman=caveman_mode)

    optimized_text = result.optimized_text
    if use_summary:
        optimized_text = extractive_summary(optimized_text, keep_ratio=keep_ratio)

    final_tokens = count_tokens(optimized_text)
    original_tokens = result.original_tokens
    saved = original_tokens - final_tokens
    percent = (saved / original_tokens * 100) if original_tokens else 0.0

    st.subheader("Results")
    m1, m2, m3 = st.columns(3)
    m1.metric("Original", f"{original_tokens:,} tok")
    m2.metric("Optimized", f"{final_tokens:,} tok")
    m3.metric("Saved", f"{saved:,} tok", f"-{percent:.0f}%")

    original_cost = measure(text, model=model).estimated_cost_usd
    optimized_cost = measure(optimized_text, model=model).estimated_cost_usd
    st.caption(
        f"Estimated cost on **{model}**: "
        f"${original_cost:.6f} → ${optimized_cost:.6f} per call "
        f"(saves ${original_cost - optimized_cost:.6f})"
    )

    # --- Visual: before vs after -----------------------------------------
    compare_df = pd.DataFrame(
        {"tokens": [original_tokens, final_tokens]},
        index=["Original", "Optimized"],
    )
    st.bar_chart(compare_df, color="#4c9be8", horizontal=True)

    st.subheader("Optimized text")
    st.code(optimized_text, language=None)
    st.download_button(
        "⬇️ Download optimized text",
        data=optimized_text,
        file_name="optimized.txt",
        mime="text/plain",
    )

    with st.expander("Per-step breakdown"):
        # A small chart of how many tokens each reducer saved.
        step_df = pd.DataFrame(
            {"tokens saved": [s.tokens_saved for s in result.steps]},
            index=[s.description for s in result.steps],
        )
        st.bar_chart(step_df, color="#7bd88f")
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
    st.info("Enter some text above (or click **Load example**) to see the savings.")
