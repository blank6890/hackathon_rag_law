"""
ComplianceMind — Streamlit UI (v4 with all Tier 1 + 2 features)

A clean interface where a user describes their business and gets an
AI-generated Indian legal compliance report with citations.

FEATURES (cumulative):
  v1: Government-gazette visual design, basic compliance check
  v2: Bug fixes (st.iframe, height, lazy Groq, IST date, etc.)
  v3: Compliance Score (0-100), Industry presets, PDF certificate,
      Severity weights + penalty, Real ChromaDB retrieval
  v4 (this version): ALL Tier 1 + 2 features —
      1. Compliance Score (0-100) with letter grade [v3]
      2. Before/After Action Plan — interactive checklist
      3. PDF certificate download [v3]
      4. Plain-English ↔ Legalese toggle per finding
      5. Comparison mode — two business descriptions side-by-side
      6. Industry presets [v3]
      7. Risk timeline — enforcement dates per finding
      8. Citation trust score per finding (direct/inferred)
      9. Ask-a-follow-up chat after the report
      10. History sidebar with past queries
      11. Multilingual notice (English/Hindi/Tamil/Bengali)
      12. Severity weights + cost estimator [v3]
      13. Real ChromaDB retrieval [v3]
      14. Role tags (Founder/Legal/Engineering/DPO/Finance)
      15. Shareable URL via query params
"""

import streamlit as st
import streamlit.components.v1 as components

from pipeline import (
    run_pipeline, answer_followup, translate_report, get_supported_languages,
)
from styles import (
    get_global_css,
    render_hero,
    render_notice_header,
    render_finding_cards,
    render_footer,
    render_timeline,
    render_comparison,
    render_action_plan,
    estimate_cards_height,
)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ComplianceMind",
    page_icon="⚖️",
    layout="centered",
)

# ── Global styling ──────────────────────────────────────────────────────────
st.markdown(get_global_css(), unsafe_allow_html=True)

# ── Session state initialization ────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []  # list of {desc, score, grade, timestamp}
if "resolved_gaps" not in st.session_state:
    st.session_state.resolved_gaps = set()  # set of "act::section" keys
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_desc" not in st.session_state:
    st.session_state.last_desc = ""

# ── Industry presets ────────────────────────────────────────────────────────
_PRESETS = {
    "🎓  EdTech": (
        "We run an online education platform that collects student names, "
        "emails, and learning progress data. We sell courses directly to "
        "consumers through our website. Students pay via UPI and credit cards. "
        "We offer refunds within 7 days of purchase."
    ),
    "💳  Fintech UPI": (
        "We are building a fintech app that lets users make UPI payments and "
        "transfer money. We collect personal data including names, phone "
        "numbers, PAN numbers, and transaction history. We also sell financial "
        "products like insurance and mutual funds to consumers online."
    ),
    "🛒  D2C E-commerce": (
        "We operate a direct-to-consumer e-commerce website selling organic "
        "skincare products. We collect customer names, shipping addresses, "
        "phone numbers, and process online payments. We run promotional "
        "discount campaigns and offer 30-day returns."
    ),
    "🩺  Health App": (
        "We are building a telemedicine app that connects patients with "
        "doctors via video calls. We collect names, age, gender, medical "
        "history, and prescription data. We process payments for "
        "consultations and store health records on our servers."
    ),
    "💼  SaaS B2B": (
        "We build a B2B SaaS project management tool for enterprise clients. "
        "We collect company names, employee emails, and usage analytics. We "
        "process annual subscription payments and store business documents "
        "and internal communications."
    ),
}

# ── Helper: run pipeline and store result ───────────────────────────────────
def _run_check(desc: str) -> dict | None:
    """Run the pipeline and store the result in session state + history."""
    with st.spinner("Analysing your business against Indian statutes…"):
        try:
            result = run_pipeline(desc)
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")
            return None

    if not result.get("needs_clarification"):
        # Add to history (keep last 10)
        st.session_state.history.insert(0, {
            "desc": desc[:120] + ("…" if len(desc) > 120 else ""),
            "full_desc": desc,
            "score": result.get("score", 0),
            "grade": result.get("grade", "—"),
            "timestamp": __import__("datetime").datetime.now().strftime("%H:%M:%S"),
        })
        st.session_state.history = st.session_state.history[:10]
        st.session_state.last_result = result
        st.session_state.last_desc = desc
        # Reset resolved gaps when a new check runs
        st.session_state.resolved_gaps = set()
        st.session_state.chat_messages = []

    return result

# ── Helper: render full results ─────────────────────────────────────────────
def _render_results(result: dict, desc: str, show_action_plan: bool = True,
                    show_chat: bool = True, key_prefix: str = ""):
    """Render the full results section: notice header, report, timeline,
    finding cards, action plan, and follow-up chat."""
    findings = result.get("findings") or []
    sources = result.get("sources") or []
    score = result.get("score", 0)
    grade = result.get("grade", "—")
    grade_color = result.get("grade_color", "#1B2A4A")
    score_summary = result.get("score_summary", "")

    # ── NOTICE OF FINDINGS masthead with score gauge ────────────────────────
    st.markdown("---")
    components.html(
        render_notice_header(
            findings,
            score=score,
            grade=grade,
            grade_color=grade_color,
            score_summary=score_summary,
        ),
        height=280,
        scrolling=False,
    )

    # ── Plain-English ↔ Legalese toggle ────────────────────────────────────
    view_mode = st.radio(
        "Report view",
        ["📖 Plain English", "📜 Full statute text"],
        horizontal=True,
        key=f"{key_prefix}view_mode",
        label_visibility="collapsed",
    )

    if view_mode == "📖 Plain English":
        # ── Render the markdown report ──────────────────────────────────────
        st.markdown(result["report"])
    else:
        # ── Render the full statute text per finding ────────────────────────
        st.markdown("### 📜 Full Statute Text per Finding")
        st.caption("The actual section text from Indian statute law, "
                   "unmodified. This is what the LLM reasoned over.")
        for src in sources:
            st.markdown(f"**{src.get('act', '')} — {src.get('section', '')}: "
                        f"{src.get('title', '')}**")
            st.info(src.get("text", ""))

    # ── Risk Timeline ──────────────────────────────────────────────────────
    if findings:
        st.markdown("---")
        components.html(render_timeline(findings), height=280, scrolling=False)

    # ── Action Plan checklist ──────────────────────────────────────────────
    if show_action_plan and findings:
        st.markdown("---")
        st.markdown("### 📋 Action Plan")
        st.caption("Check off each gap as you resolve it. The score "
                   "recalculates live based on what's still open.")

        actionable = [f for f in findings
                      if (f.get("status") or "").lower() in ("gap", "unclear")]

        if not actionable:
            st.success("✅ All reviewed sections are compliant. No action needed.")
        else:
            # Use a form with checkboxes
            with st.form(key=f"{key_prefix}action_form"):
                for f in actionable:
                    key = f"{f.get('act', '')}::{f.get('section', '')}"
                    is_resolved = key in st.session_state.resolved_gaps
                    label = f"**{f.get('section', '')}** — {f.get('act', '')}  \n{f.get('reasoning', '')}  \n👤 {f.get('role', 'Founder')}"
                    if st.checkbox(label, value=is_resolved, key=f"{key_prefix}ap_{key}"):
                        st.session_state.resolved_gaps.add(key)
                    else:
                        st.session_state.resolved_gaps.discard(key)

                # Show the live-updated score
                import copy
                adjusted_findings = copy.deepcopy(findings)
                for f in adjusted_findings:
                    key = f"{f.get('act', '')}::{f.get('section', '')}"
                    if key in st.session_state.resolved_gaps:
                        f["status"] = "compliant"  # treat resolved as compliant

                from pipeline import compute_compliance_score
                live_score = compute_compliance_score(adjusted_findings)
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric("Live Score", f"{live_score['score']}/100 ({live_score['grade']})")
                with col2:
                    st.caption(live_score["summary"])

                submitted = st.form_submit_button("Update Score", type="primary")
                if submitted:
                    st.rerun()

            # Also render the visual action plan
            components.html(
                render_action_plan(findings, st.session_state.resolved_gaps),
                height=max(200, len(actionable) * 80 + 100),
                scrolling=True,
            )

    # ── PDF certificate download ───────────────────────────────────────────
    try:
        from pdf_export import generate_certificate
        from reportlab.lib.colors import HexColor

        pdf_bytes = generate_certificate(
            business_desc=desc,
            findings=findings,
            sources=sources,
            score=score,
            grade=grade,
            grade_color=HexColor(grade_color),
            score_summary=score_summary,
        )
        st.download_button(
            label="📄  Download compliance certificate (PDF)",
            data=pdf_bytes,
            file_name=f"compliance-certificate-{grade}.pdf",
            mime="application/pdf",
            use_container_width=False,
            type="primary",
            key=f"{key_prefix}pdf_download",
        )
    except ImportError:
        st.caption("_PDF export requires `reportlab` — run `pip install reportlab` to enable._")

    # ── Sources expander (animated finding cards) ──────────────────────────
    st.markdown("---")
    with st.expander("📚  Sources used (cited statute sections)", expanded=True):
        if not sources:
            st.info("No sources were retrieved for this query.")
        else:
            components.html(
                render_finding_cards(sources, findings),
                height=estimate_cards_height(sources, findings),
                scrolling=True,
            )

    # ── Follow-up chat ─────────────────────────────────────────────────────
    if show_chat:
        st.markdown("---")
        st.markdown("### 💬 Ask a Follow-up Question")
        st.caption("Ask anything about the findings — the answer is grounded "
                   "in the same statute sections that produced the report.")

        # Display chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if question := st.chat_input("e.g. What if I only collect emails, not phone numbers?",
                                      key=f"{key_prefix}chat_input"):
            # Add user message
            st.session_state.chat_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            # Get answer
            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        answer = answer_followup(
                            question, findings, sources, desc
                        )
                    except Exception as e:
                        answer = f"Sorry, I couldn't process that: {e}"
                st.markdown(answer)
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": answer}
                )

    # ── Footer ─────────────────────────────────────────────────────────────
    components.html(render_footer(), height=90, scrolling=False)


# ── Sidebar: History + Shareable URL ───────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ ComplianceMind")
    st.caption("_A cited compliance check, not a guess._")
    st.markdown("---")

    # ── History ────────────────────────────────────────────────────────────
    st.markdown("### 📜 History")
    if not st.session_state.history:
        st.caption("_No checks yet. Run one to see it here._")
    else:
        for i, item in enumerate(st.session_state.history):
            score_color = ("#4C6B3F" if item["score"] >= 90
                           else "#B08D57" if item["score"] >= 60
                           else "#8C1D1D")
            label = f"**{item['grade']}** ({item['score']}/100) — {item['desc'][:60]}{'…' if len(item['desc']) > 60 else ''}"
            if st.button(label, key=f"hist_{i}", use_container_width=True,
                         help=item["desc"]):
                # Reload this check
                st.session_state.business_desc = item["full_desc"]
                st.rerun()

    st.markdown("---")

    # ── Shareable URL ──────────────────────────────────────────────────────
    st.markdown("### 🔗 Shareable URL")
    if st.session_state.last_desc:
        # Encode the business description in the query string
        import urllib.parse
        encoded = urllib.parse.quote(st.session_state.last_desc[:500])
        share_url = f"?q={encoded}"
        st.code(share_url, language="text")
        st.caption("Copy this query string — anyone with the URL + your "
                   "Streamlit instance can reproduce this check.")
        if st.button("📋 Copy to clipboard", key="copy_url"):
            st.info("Copy the URL above from the code block.")
    else:
        st.caption("_Run a check to generate a shareable URL._")

    st.markdown("---")

    # ── Multilingual ───────────────────────────────────────────────────────
    st.markdown("### 🌐 Language")
    langs = get_supported_languages()
    selected_lang_label = st.selectbox(
        "Translate report to",
        list(langs.keys()),
        index=0,
        key="lang_select",
    )
    selected_lang_code = langs[selected_lang_label]

    if (selected_lang_code != "en" and st.session_state.last_result
            and not st.session_state.last_result.get("needs_clarification")):
        if st.button("🔄 Translate Report", key="translate_btn",
                     use_container_width=True, type="primary"):
            with st.spinner(f"Translating to {selected_lang_label}…"):
                try:
                    translated = translate_report(
                        st.session_state.last_result["report"],
                        selected_lang_code,
                    )
                    st.session_state.translated_report = translated
                    st.rerun()
                except Exception as e:
                    st.error(f"Translation failed: {e}")

    # Show translated report if available
    if (selected_lang_code != "en"
            and "translated_report" in st.session_state
            and st.session_state.translated_report):
        st.markdown("---")
        st.markdown(f"**Translated Report ({selected_lang_label}):**")
        st.markdown(st.session_state.translated_report)
    elif selected_lang_code == "en":
        # Clear translation when switching back to English
        if "translated_report" in st.session_state:
            del st.session_state.translated_report

# ── Check for shared URL on load ────────────────────────────────────────────
import urllib.parse
qp = st.query_params
if "q" in qp and not st.session_state.last_result:
    shared_desc = urllib.parse.unquote(qp["q"])
    st.session_state.business_desc = shared_desc
    st.info(f"📥 Loaded shared business description ({len(shared_desc)} chars). "
            "Click 'Check compliance' to run the analysis.")
    if st.button("▶️  Run shared check", type="primary"):
        result = _run_check(shared_desc)
        if result and not result.get("needs_clarification"):
            st.rerun()

# ── Hero ────────────────────────────────────────────────────────────────────
components.html(render_hero(), height=200, scrolling=False)

# ── Mode selector: Single vs Compare ────────────────────────────────────────
mode = st.radio(
    "Mode",
    ["🔍  Single check", "⚖️  Compare two businesses"],
    horizontal=True,
    label_visibility="collapsed",
)

if mode == "🔍  Single check":
    # ── Industry presets ────────────────────────────────────────────────────
    if "business_desc" not in st.session_state:
        st.session_state.business_desc = ""

    st.markdown("**Quick start — pick a template:**")
    # Inject a hidden marker div so the global CSS can scope uniform-height
    # styling to ONLY this row of preset buttons (via the sibling selector
    # .cm-preset-row + [data-testid="stHorizontalBlock"]). Without this
    # marker, the CSS would either have to target ALL stButton instances
    # (which would break the primary "Check compliance" button) or use
    # fragile :has() selectors. The marker keeps the targeting precise.
    st.markdown('<div class="cm-preset-row"></div>', unsafe_allow_html=True)
    preset_cols = st.columns(len(_PRESETS))
    for i, (label, desc_text) in enumerate(_PRESETS.items()):
        if preset_cols[i].button(label, key=f"preset_{i}",
                                  use_container_width=True):
            st.session_state.business_desc = desc_text
            st.rerun()

    # ── Input ───────────────────────────────────────────────────────────────
    user_input = st.text_area(
        "Describe your business",
        value=st.session_state.business_desc,
        placeholder=(
            "E.g.: We run an online education platform that collects student "
            "names and emails. We sell courses directly to consumers…"
        ),
        height=140,
        key="single_input",
    )

    run_button = st.button("🔍  Check compliance", type="primary",
                           use_container_width=True)

    if run_button:
        if not user_input.strip():
            st.warning("Please enter a business description first.")
        else:
            result = _run_check(user_input.strip())
            if result:
                if result.get("needs_clarification"):
                    st.warning(result["message"])
                else:
                    _render_results(result, user_input.strip())

else:
    # ── Comparison mode ─────────────────────────────────────────────────────
    st.markdown("### ⚖️  Compare Two Business Models")
    st.caption("Run the compliance check on two descriptions side-by-side "
               "to see which has fewer gaps.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Business A**")
        desc_a = st.text_area(
            "Describe business A",
            value=_PRESETS["🎓  EdTech"],
            height=140,
            key="compare_a",
            label_visibility="collapsed",
        )
    with col_b:
        st.markdown("**Business B**")
        desc_b = st.text_area(
            "Describe business B",
            value=_PRESETS["💳  Fintech UPI"],
            height=140,
            key="compare_b",
            label_visibility="collapsed",
        )

    if st.button("⚖️  Compare compliance", type="primary",
                 use_container_width=True):
        if not desc_a.strip() or not desc_b.strip():
            st.warning("Please enter both business descriptions.")
        else:
            with st.spinner("Running check A…"):
                try:
                    result_a = run_pipeline(desc_a.strip())
                except Exception as e:
                    st.error(f"Check A failed: {e}")
                    st.stop()
            with st.spinner("Running check B…"):
                try:
                    result_b = run_pipeline(desc_b.strip())
                except Exception as e:
                    st.error(f"Check B failed: {e}")
                    st.stop()

            if result_a.get("needs_clarification"):
                st.warning(f"**Business A:** {result_a['message']}")
            elif result_b.get("needs_clarification"):
                st.warning(f"**Business B:** {result_b['message']}")
            else:
                # ── Comparison header ────────────────────────────────────────
                st.markdown("---")
                components.html(
                    render_comparison(
                        result_a.get("score", 0),
                        result_a.get("grade", "—"),
                        result_a.get("grade_color", "#1B2A4A"),
                        result_b.get("score", 0),
                        result_b.get("grade", "—"),
                        result_b.get("grade_color", "#1B2A4A"),
                        "Business A",
                        "Business B",
                        result_a.get("findings", []),
                        result_b.get("findings", []),
                    ),
                    height=320,
                    scrolling=False,
                )

                # ── Detailed findings side-by-side ───────────────────────────
                st.markdown("### Detailed Findings")
                det_a, det_b = st.columns(2)
                with det_a:
                    st.markdown(f"#### Business A — Score {result_a.get('score', 0)}/100")
                    st.markdown(result_a["report"])
                    findings_a = result_a.get("findings") or []
                    if findings_a:
                        with st.expander("📊 Business A findings detail", expanded=False):
                            for f in findings_a:
                                status = f.get("status", "—").upper()
                                sev = f.get("severity", "—").upper()
                                st.markdown(f"- **{f.get('section', '')}** ({f.get('act', '')}) "
                                            f"— {status} / {sev}  \n  {f.get('reasoning', '')}")
                with det_b:
                    st.markdown(f"#### Business B — Score {result_b.get('score', 0)}/100")
                    st.markdown(result_b["report"])
                    findings_b = result_b.get("findings") or []
                    if findings_b:
                        with st.expander("📊 Business B findings detail", expanded=False):
                            for f in findings_b:
                                status = f.get("status", "—").upper()
                                sev = f.get("severity", "—").upper()
                                st.markdown(f"- **{f.get('section', '')}** ({f.get('act', '')}) "
                                            f"— {status} / {sev}  \n  {f.get('reasoning', '')}")

                # ── PDF download for the winner ──────────────────────────────
                winner = ("A" if result_a.get("score", 0) > result_b.get("score", 0)
                          else "B" if result_b.get("score", 0) > result_a.get("score", 0)
                          else "tie")
                if winner != "tie":
                    winner_result = result_a if winner == "A" else result_b
                    winner_desc = desc_a.strip() if winner == "A" else desc_b.strip()
                    try:
                        from pdf_export import generate_certificate
                        from reportlab.lib.colors import HexColor
                        pdf_bytes = generate_certificate(
                            business_desc=winner_desc,
                            findings=winner_result.get("findings", []),
                            sources=winner_result.get("sources", []),
                            score=winner_result.get("score", 0),
                            grade=winner_result.get("grade", "—"),
                            grade_color=HexColor(winner_result.get("grade_color", "#1B2A4A")),
                            score_summary=winner_result.get("score_summary", ""),
                        )
                        st.download_button(
                            label=f"📄  Download winner (Business {winner}) certificate (PDF)",
                            data=pdf_bytes,
                            file_name=f"compliance-winner-{winner}.pdf",
                            mime="application/pdf",
                            type="primary",
                        )
                    except ImportError:
                        pass

                components.html(render_footer(), height=90, scrolling=False)
