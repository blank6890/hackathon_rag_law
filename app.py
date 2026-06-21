"""
ComplianceMind — Streamlit UI

A clean interface where a user describes their business and gets an
AI-generated Indian legal compliance report with citations.
"""

import streamlit as st
from pipeline import run_pipeline

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ComplianceMind",
    page_icon="⚖️",
    layout="centered",
)

# ── Custom styling ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Slightly tighter layout */
    .block-container { max-width: 720px; }

    /* Source cards in the expander */
    .source-card {
        background: #f8f9fa;
        border-left: 4px solid #4A90D9;
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 4px;
    }
    .source-card h4 { margin: 0 0 4px 0; font-size: 0.95rem; }
    .source-card p  { margin: 0; font-size: 0.88rem; color: #444; }
    .source-card .section-tag {
        display: inline-block;
        background: #E3F2FD;
        color: #1565C0;
        font-size: 0.78rem;
        padding: 2px 8px;
        border-radius: 3px;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.title("⚖️ ComplianceMind")
st.caption(
    "Describe your business in plain English and find out which Indian laws "
    "apply — with every claim cited to a real statute section."
)

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

            # -- Sources expander ------------------------------------------
            st.markdown("---")
            with st.expander("📚 Sources used", expanded=False):
                if not result.get("sources"):
                    st.info("No sources were retrieved for this query.")
                else:
                    for src in result["sources"]:
                        st.markdown(
                            f"""<div class="source-card">
                                <span class="section-tag">{src['section']}</span>
                                <h4>{src['act']}</h4>
                                <p><strong>{src['title']}</strong></p>
                                <p>{src['text']}</p>
                            </div>""",
                            unsafe_allow_html=True,
                        )
