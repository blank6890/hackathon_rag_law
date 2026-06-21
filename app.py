"""
ComplianceMind — Streamlit UI

A clean interface where a user describes their business and gets an
AI-generated Indian legal compliance report with citations.

Styling: "Government Gazette" design system (see styles.py). Native
Streamlit widgets are restyled via CSS injection; the hero banner and
finding cards are custom HTML/CSS/JS rendered through components.v1.html()
for real scroll-triggered motion.
"""

import streamlit as st

from pipeline import run_pipeline
from styles import get_global_css, render_hero, render_finding_cards

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ComplianceMind",
    page_icon="⚖️",
    layout="centered",
)

# ── Global styling (restyles native Streamlit widgets) ─────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)

# ── Hero ─────────────────────────────────────────────────────────────────────
st.iframe(render_hero(), height="content")

# ── Input ───────────────────────────────────────────────────────────────────
user_input = st.text_area(
    "Describe your business",
    placeholder=(
        "E.g.: We run an online education platform that collects student "
        "names and emails. We sell courses directly to consumers…"
    ),
    height=140,
)

run_button = st.button("🔍 Check compliance", type="primary", use_container_width=True)

# ── Pipeline execution ──────────────────────────────────────────────────────
if run_button:
    if not user_input.strip():
        st.warning("Please enter a business description first.")
    else:
        with st.spinner("Analysing your business against Indian statutes…"):
            try:
                result = run_pipeline(user_input.strip())
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")
                st.stop()

        # -- Vague input → ask for clarification --------------------------
        if result.get("needs_clarification"):
            st.warning(result["message"])
        else:
            # -- Render the markdown report --------------------------------
            st.markdown("---")
            st.markdown(result["report"])

            # -- Sources expander (animated finding cards) ------------------
            st.markdown("---")
            # NOTE: expanded=True is required here, not just a UX choice.
            # st.iframe(height="content") measures the iframe's rendered
            # layout height in the browser — but a *collapsed* expander
            # hides its body with display:none, and display:none elements
            # always measure as 0px. If this defaulted to collapsed, the
            # cards iframe would lock in at 0 height before the user ever
            # opened the panel, and never re-measure. Defaulting open avoids
            # the race entirely.
            with st.expander("📚 Sources used", expanded=True):
                sources = result.get("sources") or []
                if not sources:
                    st.info("No sources were retrieved for this query.")
                else:
                    st.iframe(
                        render_finding_cards(sources, result.get("findings")),
                        height="content",
                    )
