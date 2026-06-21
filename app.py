"""
ComplianceMind — Streamlit UI

A clean interface where a user describes their business and gets an
AI-generated Indian legal compliance report with citations.

Styling: "Government Gazette" design system (see styles.py). Native
Streamlit widgets are restyled via CSS injection; the hero banner,
notice masthead, finding cards and footer are custom HTML/CSS/JS
rendered through streamlit.components.v1.html() for real scroll-triggered
motion and proper height auto-sizing.

BUGFIXES vs original:
  1. Replaced non-existent st.iframe() with components.v1.html().
  2. Removed invalid height="content" arg — html() needs an integer.
     We now pass an explicit pixel height for the hero (which is fixed)
     and use estimate_cards_height() for the variable-height finding
     cards (see fix #7 below).
  3. Imported streamlit.components.v1 explicitly.
  4. Added a "NOTICE OF FINDINGS" masthead above the report (per design
     brief) with a live tally of compliant / gap / unclear counts.
  5. Added a footer signature block.
  6. Fixed _today_ist() in styles.py — original returned UTC date, not
     IST. Now uses Asia/Kolkata timezone.
  7. Fixed finding-cards height calculation — original used
     `len(sources) * 220` which silently clipped long statute texts
     (corpus has sections up to ~6700 chars; a 4-source result with
     CPA Section 2(47) renders at ~3446px but the old formula gave
     only 880px, clipping 75% of the cards). New helper
     estimate_cards_height() computes an accurate height based on
     actual text length per card.
  8. Removed misleading postMessage('streamlit:setFrameHeight') JS —
     that protocol only works for custom declare_component() components,
     NOT for components.html(). The iframe height is now set correctly
     up-front via estimate_cards_height(), and scrolling=True is used
     as a safety net.
  9. Cleaned up render_footer() — original used a fragile
     .replace('{date}', ...) pattern that worked but was obscure and
     would break if the date string ever contained { or }.
"""

import streamlit as st
import streamlit.components.v1 as components

from pipeline import run_pipeline
from styles import (
    get_global_css,
    render_hero,
    render_notice_header,
    render_finding_cards,
    render_footer,
    estimate_cards_height,
)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ComplianceMind",
    page_icon="⚖️",
    layout="centered",
)

# ── Global styling (restyles native Streamlit widgets) ─────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)

# ── Hero (letterhead masthead) ─────────────────────────────────────────────
# Hero is a fixed-size block — give it an explicit pixel height so the
# components.html() iframe doesn't clip or scroll.
components.html(render_hero(), height=200, scrolling=False)

# ── Input ───────────────────────────────────────────────────────────────────
user_input = st.text_area(
    "Describe your business",
    placeholder=(
        "E.g.: We run an online education platform that collects student "
        "names and emails. We sell courses directly to consumers…"
    ),
    height=140,
)

run_button = st.button(
    "🔍  Check compliance",
    type="primary",
    use_container_width=True,
)

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
            findings = result.get("findings") or []
            sources = result.get("sources") or []

            # -- NOTICE OF FINDINGS masthead with live tally ---------------
            st.markdown("---")
            components.html(
                render_notice_header(findings),
                height=240,
                scrolling=False,
            )

            # -- Render the markdown report --------------------------------
            st.markdown(result["report"])

            # -- Sources expander (animated finding cards) ------------------
            st.markdown("---")
            # NOTE: expanded=True is intentional. components.html() measures
            # the iframe's rendered layout height in the browser — but a
            # *collapsed* expander hides its body with display:none, and
            # display:none elements always measure as 0px. If this defaulted
            # to collapsed, the cards iframe would lock in at 0 height
            # before the user ever opened the panel, and never re-measure.
            # Defaulting open avoids the race entirely.
            with st.expander("📚  Sources used (cited statute sections)",
                             expanded=True):
                if not sources:
                    st.info("No sources were retrieved for this query.")
                else:
                    # BUGFIX: original used `len(sources) * 220` which
                    # silently clipped long statute texts (the corpus has
                    # sections up to ~6700 chars; a 4-source result with
                    # CPA Section 2(47) renders at ~3446px but the old
                    # formula gave only 880px, clipping 75% of the cards).
                    # estimate_cards_height() computes an accurate height
                    # based on actual text length per card. We also pass
                    # scrolling=True as a safety net for any residual
                    # miscalculation (e.g. user has a very narrow viewport
                    # that forces more line-wrapping than estimated).
                    components.html(
                        render_finding_cards(sources, findings),
                        height=estimate_cards_height(sources),
                        scrolling=True,
                    )

            # -- Footer signature block ------------------------------------
            components.html(render_footer(), height=90, scrolling=False)
