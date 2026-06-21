"""
ComplianceMind — "Government Gazette" design system.

A real-world government legal notice is the closest artifact to what this
tool produces, so the entire visual language is built around that metaphor:

  • ivory paper background, ink-black body, navy headings
  • a letterhead strip with file-reference number in mono
  • an official seal / emblem drawn purely in CSS (no image asset)
  • a "NOTICE OF FINDINGS" masthead framing the results
  • per-finding circular seal stamps that bear the act abbreviation
    (DPDP, ITA, CPA, GST, ECOM) — visually saying "this claim has been
    officially verified", which is the product pitch in one element

Two delivery mechanisms:
  1. get_global_css() — injected via st.markdown(unsafe_allow_html=True) to
     restyle Streamlit's native widgets (text area, button, expander, alerts)
     so they match the token system below.
  2. render_hero() / render_notice_header() / render_finding_cards() —
     self-contained HTML/CSS/JS strings rendered via
     streamlit.components.v1.html() for the decorative, scroll-animated
     elements that native CSS injection can't drive.

Design tokens are LOCKED per the brief — do not introduce new hex values.
"""

import html
import re

# ── Locked color tokens (per design brief) ─────────────────────────────────
PAPER = "#F7F5F0"            # ivory paper background
INK = "#1A1A1A"              # primary text
NAVY = "#1B2A4A"             # official navy (primary accent)
SEAL_RED = "#8C1D1D"         # seal red (status / alert accent)
GOLD = "#B08D57"             # emblem gold (secondary accent)
COMPLIANT_GREEN = "#4C6B3F"  # muted olive-green for "compliant" status
RULE_GREY = "rgba(26,26,26,0.10)"  # hairline rules between sections

# ── Motion + card tokens ────────────────────────────────────────────────────
CARD_RADIUS = "14px"
CARD_SHADOW = "0 1px 3px rgba(26,26,26,0.06), 0 4px 14px rgba(26,26,26,0.05)"
CARD_SHADOW_LIFT = "0 2px 6px rgba(26,26,26,0.08), 0 10px 28px rgba(26,26,26,0.10)"
CARD_BORDER = "1px solid rgba(27,42,74,0.10)"
MOTION_DURATION = "420ms"
MOTION_EASE = "cubic-bezier(0.16, 1, 0.3, 1)"  # soft "ease-out-expo" landing

# ── Typography ─────────────────────────────────────────────────────────────
FONT_DISPLAY = "'Source Serif 4', 'Lora', Georgia, serif"
FONT_BODY = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_MONO = "'IBM Plex Mono', 'SFMono-Regular', Menlo, monospace"

GOOGLE_FONTS_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&"
    "family=IBM+Plex+Sans:wght@400;500;600;700&"
    "family=IBM+Plex+Mono:wght@400;500;600&display=swap');"
)

_STATUS_COLORS = {
    "compliant": COMPLIANT_GREEN,
    "gap": SEAL_RED,
    "unclear": GOLD,
}

_STATUS_LABELS = {
    "compliant": "COMPLIANT",
    "gap": "GAP FOUND",
    "unclear": "UNCLEAR",
}

# ── Act abbreviation lookup for seal stamps ────────────────────────────────
# Each finding's seal bears the abbreviation of the act it cites — visually
# echoing how a real government stamp bears the issuing department's seal.
_ACT_ABBREVIATIONS = [
    # (regex pattern, abbreviation shown on the seal)
    (r"digital personal data protection|dpdp", "DPDP"),
    (r"information technology|it act|itact", "ITA"),
    (r"consumer protection.*e-commerce|e-commerce rule", "ECOM"),
    (r"consumer protection|cpa", "CPA"),
    (r"goods and services tax|gst", "GST"),
]


def _act_abbreviation(act_name: str) -> str:
    """Return a 2-5 letter abbreviation for the act, used on the seal stamp."""
    if not act_name:
        return "§"
    low = act_name.lower()
    for pattern, abbr in _ACT_ABBREVIATIONS:
        if re.search(pattern, low):
            return abbr
    # Fallback: first letters of significant words
    words = [w for w in re.findall(r"[A-Za-z]+", act_name)
             if w.lower() not in {"act", "the", "of", "and", "for"}]
    return "".join(w[0] for w in words[:4]).upper() or "§"


# ============================================================================
# 1. Global CSS — restyles Streamlit's own widgets
# ============================================================================
def get_global_css() -> str:
    return f"""
<style>
{GOOGLE_FONTS_IMPORT}

/* ── Top header / toolbar (the "Deploy" bar) ─────────────────────────────
   Unstyled, this defaults to Streamlit's own theme (often a stark black
   bar). Retint it to read as a quiet letterhead strip. */
header[data-testid="stHeader"] {{
    background: {PAPER} !important;
    border-bottom: 1px solid {RULE_GREY};
}}
[data-testid="stToolbar"],
[data-testid="stToolbarActions"],
[data-testid="stMainMenu"] {{
    color: {NAVY} !important;
}}
[data-testid="stToolbarActions"] svg,
[data-testid="stMainMenu"] svg {{
    fill: {NAVY} !important;
}}
[data-testid="stToolbarActions"] button:hover,
[data-testid="stMainMenu"] button:hover {{
    background: rgba(27,42,74,0.08) !important;
}}
[data-testid="stDecoration"] {{
    background: linear-gradient(90deg, {NAVY}, {GOLD}) !important;
    height: 3px !important;
}}
[data-testid="stStatusWidget"] {{
    color: {NAVY} !important;
}}

/* ── App background & layout width ─────────────────────────────────────── */
.stApp {{
    background: {PAPER};
    /* Subtle paper-grain via layered radial gradients — barely visible,
       but breaks up the flat ivory and reads as "official document". */
    background-image:
        radial-gradient(circle at 20% 30%, rgba(176,141,87,0.025) 0%, transparent 50%),
        radial-gradient(circle at 80% 70%, rgba(27,42,74,0.018) 0%, transparent 50%);
}}
.block-container {{
    max-width: 780px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
}}

/* ── Typography ───────────────────────────────────────────────────────── */
.stApp, .stApp p, .stApp li, .stApp label, .stMarkdown {{
    font-family: {FONT_BODY};
    color: {INK};
    line-height: 1.65;
}}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
    font-family: {FONT_DISPLAY};
    color: {NAVY};
    font-weight: 600;
    letter-spacing: -0.01em;
}}
.stApp h1 {{ font-size: 2.1rem; }}
.stApp h2 {{ font-size: 1.5rem; margin-top: 2rem; }}
.stApp h3 {{ font-size: 1.2rem; }}
code, .stMarkdown code {{
    font-family: {FONT_MONO};
    background: rgba(27,42,74,0.06);
    color: {NAVY};
    padding: 0.1em 0.4em;
    border-radius: 4px;
    font-size: 0.85em;
}}
/* Body markdown rendered from the LLM report — keep readable line length
   and ensure bullet lists don't get justify-stretched (per project rule). */
.stMarkdown ul, .stMarkdown ol {{
    padding-left: 1.4em;
}}
.stMarkdown li {{
    margin-bottom: 0.4em;
    text-align: left;
}}
.stMarkdown strong {{
    color: {NAVY};
    font-weight: 600;
}}

/* Native st.caption() — quiet fallback */
[data-testid="stCaptionContainer"] {{
    font-family: {FONT_BODY};
    color: {INK};
    opacity: 0.65;
}}

/* ── Text area ────────────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea {{
    font-family: {FONT_BODY};
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.18);
    border-radius: 10px;
    color: {INK};
    padding: 14px 16px;
    box-shadow: {CARD_SHADOW};
    transition: border-color {MOTION_DURATION} {MOTION_EASE},
                box-shadow {MOTION_DURATION} {MOTION_EASE};
}}
[data-testid="stTextArea"] textarea:focus {{
    border-color: {NAVY};
    box-shadow: 0 0 0 3px rgba(27,42,74,0.12), {CARD_SHADOW};
    outline: none;
}}
[data-testid="stTextArea"] textarea::placeholder {{
    color: {INK};
    opacity: 0.4;
}}
[data-testid="stWidgetLabel"] p {{
    font-family: {FONT_BODY};
    font-weight: 500;
    color: {NAVY};
}}

/* ── Accessibility: visible keyboard focus, respect reduced motion ─────── */
[data-testid="stButton"] button:focus-visible,
[data-testid="stTextArea"] textarea:focus-visible {{
    outline: 2px solid {GOLD};
    outline-offset: 2px;
}}
@media (prefers-reduced-motion: reduce) {{
    * {{ animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }}
}}

/* ── Primary button ───────────────────────────────────────────────────── */
[data-testid="stButton"] button {{
    font-family: {FONT_BODY};
    font-weight: 600;
    background: {NAVY};
    color: {PAPER};
    border: none;
    border-radius: 10px;
    padding: 0.7rem 1.2rem;
    letter-spacing: 0.01em;
    box-shadow: 0 2px 8px rgba(27,42,74,0.25);
    transition: transform {MOTION_DURATION} {MOTION_EASE},
                box-shadow {MOTION_DURATION} {MOTION_EASE},
                background {MOTION_DURATION} {MOTION_EASE};
}}
[data-testid="stButton"] button:hover {{
    background: #243a63;
    box-shadow: 0 4px 14px rgba(27,42,74,0.32);
    transform: translateY(-1px);
}}
[data-testid="stButton"] button:active {{
    transform: translateY(0px);
}}

/* ── Expander (Sources panel) ─────────────────────────────────────────── */
[data-testid="stExpander"] {{
    border: 1px solid rgba(27,42,74,0.12);
    border-radius: {CARD_RADIUS};
    background: #FFFFFF;
    box-shadow: {CARD_SHADOW};
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{
    font-family: {FONT_BODY};
    font-weight: 600;
    color: {NAVY};
}}

/* ── Alerts (warning / info / error) ─────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 10px;
    font-family: {FONT_BODY};
}}

/* ── Divider ──────────────────────────────────────────────────────────── */
hr {{
    border-color: {RULE_GREY} !important;
    margin: 2rem 0 !important;
}}

/* ── Spinner text ─────────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {{
    font-family: {FONT_BODY};
    color: {NAVY};
}}
</style>
"""


# ============================================================================
# 2. Hero banner — letterhead-style masthead
# ============================================================================
def render_hero() -> str:
    """Official letterhead hero: emblem + masthead + tagline + ref number.

    Pure CSS — no image asset. The emblem is a layered radial-gradient disc
    with a gold rim and a dashed inner ring, reading as a stamped wax seal.
    A mono "Ref. No." in the corner completes the official-document feel.
    """
    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-hero {{
    font-family: {FONT_BODY};
    background: {PAPER};
    padding: 4px 4px 18px 4px;
    opacity: 0;
    transform: translateY(14px);
    animation: cmHeroIn {MOTION_DURATION} {MOTION_EASE} forwards;
}}
@keyframes cmHeroIn {{
    to {{ opacity: 1; transform: translateY(0); }}
}}

/* Top hairline strip + file reference number — like a real letterhead */
.cm-letterhead-strip {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 12px;
    margin-bottom: 18px;
    border-bottom: 1px solid {RULE_GREY};
}}
.cm-letterhead-strip .cm-rule {{
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, {RULE_GREY}, transparent);
}}
.cm-ref {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    letter-spacing: 0.10em;
    color: {NAVY};
    opacity: 0.55;
    text-transform: uppercase;
    white-space: nowrap;
}}

.cm-hero-row {{
    display: flex;
    align-items: center;
    gap: 22px;
}}

/* Emblem — pure CSS, layered like a wax seal */
.cm-emblem {{
    flex: 0 0 auto;
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #2a4068 0%, {NAVY} 55%, #142036 100%);
    border: 3px solid {GOLD};
    box-shadow: 0 4px 14px rgba(27,42,74,0.35),
                inset 0 0 0 3px rgba(247,245,240,0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}
.cm-emblem::before {{
    content: "";
    position: absolute;
    inset: 7px;
    border-radius: 50%;
    border: 1px dashed rgba(247,245,240,0.4);
}}
.cm-emblem-glyph {{
    font-family: {FONT_DISPLAY};
    color: {GOLD};
    font-size: 30px;
    font-weight: 600;
    line-height: 1;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}}

.cm-hero-text h1 {{
    font-family: {FONT_DISPLAY};
    font-weight: 700;
    font-size: clamp(2.0rem, 4.5vw, 2.8rem);
    line-height: 1.05;
    letter-spacing: -0.015em;
    color: {NAVY};
    margin: 0 0 4px 0;
    display: flex;
    align-items: center;
    gap: 12px;
}}
.cm-hero-text h1 .cm-scales {{
    color: {GOLD};
    font-size: 0.85em;
}}
.cm-hero-text p {{
    font-family: {FONT_BODY};
    font-size: 0.95rem;
    color: {INK};
    opacity: 0.72;
    margin: 0;
    max-width: 48ch;
    line-height: 1.5;
}}
.cm-tagline {{
    font-family: {FONT_MONO};
    font-size: 0.66rem;
    letter-spacing: 0.16em;
    color: {SEAL_RED};
    text-transform: uppercase;
    margin-top: 10px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}}
.cm-tagline::before {{
    content: "";
    display: inline-block;
    width: 18px;
    height: 1px;
    background: {SEAL_RED};
}}

@media (prefers-reduced-motion: reduce) {{
    .cm-hero {{ animation: none; opacity: 1; transform: none; }}
}}
@media (max-width: 520px) {{
    .cm-emblem {{ width: 56px; height: 56px; }}
    .cm-emblem-glyph {{ font-size: 22px; }}
    .cm-hero-row {{ gap: 14px; }}
}}
</style>

<div class="cm-hero">
    <div class="cm-letterhead-strip">
        <span class="cm-ref">Ref. No. CM/2026/XXXX</span>
        <span class="cm-rule"></span>
        <span class="cm-ref">Issued electronically</span>
    </div>
    <div class="cm-hero-row">
        <div class="cm-emblem"><span class="cm-emblem-glyph">&#9878;</span></div>
        <div class="cm-hero-text">
            <h1><span class="cm-scales">&#9878;</span>ComplianceMind</h1>
            <p>Describe your business in plain English and find out which
               Indian laws apply &mdash; with every claim cited to a real
               statute section.</p>
            <span class="cm-tagline">A cited compliance check, not a guess</span>
        </div>
    </div>
</div>
"""


# ============================================================================
# 3. NOTICE OF FINDINGS masthead — frames the results section
# ============================================================================
def render_notice_header(findings: list[dict] | None = None) -> str:
    """A formal 'NOTICE OF FINDINGS' masthead that sits above the report.

    Doubles as a summary stat block: counts of compliant / gap / unclear
    items are shown as small mono-set tallies on the right, like a docket.
    """
    findings = findings or []
    counts = {"compliant": 0, "gap": 0, "unclear": 0}
    for f in findings:
        s = (f.get("status") or "").lower()
        if s in counts:
            counts[s] += 1
    total = sum(counts.values())

    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-notice {{
    font-family: {FONT_BODY};
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.14);
    border-top: 4px solid {NAVY};
    border-radius: {CARD_RADIUS};
    padding: 22px 26px 18px 26px;
    box-shadow: {CARD_SHADOW};
    margin: 6px 0 18px 0;
    opacity: 0;
    transform: translateY(12px);
    animation: cmNoticeIn {MOTION_DURATION} {MOTION_EASE} forwards;
    position: relative;
    overflow: hidden;
}}
@keyframes cmNoticeIn {{
    to {{ opacity: 1; transform: translateY(0); }}
}}
/* faint corner watermark */
.cm-notice::after {{
    content: "";
    position: absolute;
    top: -28px;
    right: -28px;
    width: 110px;
    height: 110px;
    border: 1px solid rgba(176,141,87,0.18);
    border-radius: 50%;
    pointer-events: none;
}}
.cm-notice-eyebrow {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    letter-spacing: 0.18em;
    color: {SEAL_RED};
    text-transform: uppercase;
    margin-bottom: 6px;
}}
.cm-notice-title {{
    font-family: {FONT_DISPLAY};
    font-weight: 700;
    font-size: 1.6rem;
    color: {NAVY};
    margin: 0 0 6px 0;
    letter-spacing: -0.01em;
}}
.cm-notice-sub {{
    font-size: 0.88rem;
    color: {INK};
    opacity: 0.7;
    margin: 0 0 14px 0;
    max-width: 52ch;
}}
.cm-notice-tally {{
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    padding-top: 12px;
    border-top: 1px dashed {RULE_GREY};
}}
.cm-tally-item {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}
.cm-tally-num {{
    font-family: {FONT_DISPLAY};
    font-size: 1.4rem;
    font-weight: 700;
    line-height: 1;
    color: {NAVY};
}}
.cm-tally-num.is-gap {{ color: {SEAL_RED}; }}
.cm-tally-num.is-compliant {{ color: {COMPLIANT_GREEN}; }}
.cm-tally-num.is-unclear {{ color: {GOLD}; }}
.cm-tally-label {{
    font-family: {FONT_MONO};
    font-size: 0.6rem;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: {INK};
    opacity: 0.6;
}}
@media (prefers-reduced-motion: reduce) {{
    .cm-notice {{ animation: none; opacity: 1; transform: none; }}
}}
</style>

<div class="cm-notice">
    <div class="cm-notice-eyebrow">Official Communication</div>
    <h2 class="cm-notice-title">Notice of Findings</h2>
    <p class="cm-notice-sub">The following compliance assessment has been
       prepared from the business description you submitted. Each finding
       is grounded in a specific provision of Indian statute law.</p>
    <div class="cm-notice-tally">
        <div class="cm-tally-item">
            <span class="cm-tally-num">{total}</span>
            <span class="cm-tally-label">Total Reviewed</span>
        </div>
        <div class="cm-tally-item">
            <span class="cm-tally-num is-gap">{counts['gap']}</span>
            <span class="cm-tally-label">Gaps Found</span>
        </div>
        <div class="cm-tally-item">
            <span class="cm-tally-num is-unclear">{counts['unclear']}</span>
            <span class="cm-tally-label">Unclear</span>
        </div>
        <div class="cm-tally-item">
            <span class="cm-tally-num is-compliant">{counts['compliant']}</span>
            <span class="cm-tally-label">Compliant</span>
        </div>
    </div>
</div>
"""


# ============================================================================
# 4. Finding / source cards — with per-act circular seal stamps
# ============================================================================
def _status_label(status: str) -> str:
    return _STATUS_LABELS.get((status or "").lower(), "")


def render_finding_cards(sources: list[dict], findings: list[dict] | None = None) -> str:
    """Render all source/finding cards as one animated HTML block.

    Each card carries a small CSS-drawn circular seal stamp bearing the act
    abbreviation (DPDP / ITA / CPA / GST / ECOM) — visually saying "this
    claim has been officially verified", which is the entire pitch in one
    visual element. The stamp lands with a slightly bouncier motion to
    feel like a rubber stamp being pressed onto paper.

    Includes a staggered IntersectionObserver-based reveal animation. The
    iframe height is computed up-front by estimate_cards_height() and
    passed to components.html() — see that function's docstring for why
    postMessage-based auto-resize is not used.
    """
    findings = findings or []
    status_by_section = {
        (f.get("act"), f.get("section")): f.get("status") for f in findings
    }

    cards_html = []
    for i, src in enumerate(sources):
        act = html.escape(src.get("act", ""))
        section = html.escape(src.get("section", ""))
        title = html.escape(src.get("title", ""))
        text = html.escape(src.get("text", ""))
        status = status_by_section.get((src.get("act"), src.get("section")))
        status_color = _STATUS_COLORS.get(status, GOLD) if status else GOLD
        status_label = html.escape(_status_label(status)) if status else ""
        act_abbr = html.escape(_act_abbreviation(src.get("act", "")))

        delay_ms = i * 90  # staggered reveal across cards

        cards_html.append(f"""
        <article class="cm-card" data-cm-delay="{delay_ms}">
            <div class="cm-card-top">
                <span class="cm-tag">{section}</span>
                {f'<span class="cm-status" style="--status-color:{status_color}">{status_label}</span>' if status_label else ''}
            </div>
            <h4>{act}</h4>
            <p class="cm-card-subtitle"><strong>{title}</strong></p>
            <p class="cm-card-body">{text}</p>
            <div class="cm-stamp" aria-hidden="true" title="Verified: {act_abbr}">
                <div class="cm-stamp-ring">
                    <span class="cm-stamp-text">{act_abbr}</span>
                </div>
            </div>
        </article>
        """)

    cards_markup = "\n".join(cards_html)

    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-grid {{
    font-family: {FONT_BODY};
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 4px 2px 20px 2px;
}}
.cm-card {{
    position: relative;
    background: #FFFFFF;
    border-radius: {CARD_RADIUS};
    box-shadow: {CARD_SHADOW};
    border: {CARD_BORDER};
    padding: 22px 84px 22px 22px;  /* right padding reserves room for the stamp */
    opacity: 0;
    transform: translateY(22px);
    transition: opacity {MOTION_DURATION} {MOTION_EASE},
                transform {MOTION_DURATION} {MOTION_EASE},
                box-shadow 220ms ease;
}}
.cm-card:hover {{
    box-shadow: {CARD_SHADOW_LIFT};
    transform: translateY(-2px);
}}
.cm-card.cm-visible {{
    opacity: 1;
    transform: translateY(0);
}}
.cm-card-top {{
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 10px;
    margin-bottom: 10px;
}}
.cm-tag {{
    font-family: {FONT_MONO};
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    background: rgba(27,42,74,0.08);
    color: {NAVY};
    padding: 3px 9px;
    border-radius: 4px;
}}
.cm-status {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--status-color);
    padding: 3px 9px;
    border: 1px solid var(--status-color);
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}}
.cm-status::before {{
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--status-color);
}}
.cm-card h4 {{
    font-family: {FONT_DISPLAY};
    color: {NAVY};
    font-weight: 600;
    font-size: 1.06rem;
    margin: 0 0 4px 0;
    line-height: 1.3;
    padding-right: 4px;
}}
.cm-card-subtitle {{
    margin: 0 0 10px 0;
    font-size: 0.88rem;
    color: {INK};
    opacity: 0.85;
}}
.cm-card-body {{
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.62;
    color: {INK};
    opacity: 0.78;
    /* Cited statute text reads like a quoted legal passage */
    border-left: 2px solid rgba(176,141,87,0.45);
    padding-left: 12px;
}}

/* ── Seal stamp — pure CSS, no image asset ──────────────────────────────
   Bears the act abbreviation (DPDP / ITA / CPA / GST / ECOM).
   Bouncy cubic-bezier on reveal reads like a rubber stamp being pressed. */
.cm-stamp {{
    position: absolute;
    top: 18px;
    right: 18px;
    opacity: 0;
    transform: scale(0.4) rotate(-30deg);
    transition: opacity {MOTION_DURATION} cubic-bezier(0.34, 1.56, 0.64, 1),
                transform {MOTION_DURATION} cubic-bezier(0.34, 1.56, 0.64, 1);
    pointer-events: none;
}}
.cm-card.cm-visible .cm-stamp {{
    opacity: 0.92;
    transform: scale(1) rotate(-9deg);
}}
.cm-stamp-ring {{
    width: 58px;
    height: 58px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #a8332f 0%, {SEAL_RED} 60%, #6e1414 100%);
    border: 2px solid {SEAL_RED};
    box-shadow: inset 0 0 0 3px rgba(247,245,240,0.55),
                0 1px 3px rgba(0,0,0,0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}
.cm-stamp-ring::before {{
    content: "";
    position: absolute;
    inset: 5px;
    border-radius: 50%;
    border: 1px dashed rgba(247,245,240,0.55);
}}
.cm-stamp-text {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: {PAPER};
    text-align: center;
    line-height: 1;
    text-shadow: 0 1px 1px rgba(0,0,0,0.25);
}}

@media (prefers-reduced-motion: reduce) {{
    .cm-card, .cm-stamp {{ transition: none !important; }}
    .cm-card {{ opacity: 1; transform: none; }}
    .cm-stamp {{ opacity: 0.92; transform: scale(1) rotate(-9deg); }}
}}
@media (max-width: 520px) {{
    .cm-card {{ padding: 18px 64px 18px 18px; }}
    .cm-stamp-ring {{ width: 46px; height: 46px; }}
    .cm-stamp-text {{ font-size: 0.55rem; }}
}}
</style>

<div class="cm-grid" id="cm-grid">
{cards_markup}
</div>

<script>
(function() {{
    var cards = Array.prototype.slice.call(document.querySelectorAll('.cm-card'));
    var reduceMotion = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function reveal(card) {{
        var delay = parseInt(card.getAttribute('data-cm-delay') || '0', 10);
        setTimeout(function() {{ card.classList.add('cm-visible'); }}, delay);
    }}

    if (reduceMotion) {{
        cards.forEach(function(card) {{ card.classList.add('cm-visible'); }});
    }} else if ('IntersectionObserver' in window) {{
        var io = new IntersectionObserver(function(entries) {{
            entries.forEach(function(entry) {{
                if (entry.isIntersecting) {{
                    reveal(entry.target);
                    io.unobserve(entry.target);
                }}
            }});
        }}, {{ threshold: 0.15, rootMargin: "-8% 0px -8% 0px" }});
        cards.forEach(function(card) {{ io.observe(card); }});
    }} else {{
        cards.forEach(reveal);
    }}
}})();
</script>
"""


# ============================================================================
# 5. Footer signature block — bottom of the page
# ============================================================================
def render_footer() -> str:
    """A quiet signature block at the foot of the notice, like the
    'Issued by' line on a real government communication."""
    date_str = _today_ist()
    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-footer {{
    font-family: {FONT_BODY};
    margin-top: 8px;
    padding-top: 18px;
    border-top: 1px solid {RULE_GREY};
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    flex-wrap: wrap;
    color: {INK};
    opacity: 0.7;
}}
.cm-footer-left {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.cm-footer-mark {{
    font-family: {FONT_DISPLAY};
    font-size: 1.1rem;
    color: {NAVY};
    font-weight: 600;
}}
.cm-footer-tag {{
    font-family: {FONT_MONO};
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {INK};
    opacity: 0.55;
}}
.cm-footer-meta {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    color: {INK};
    opacity: 0.5;
    text-align: right;
    line-height: 1.5;
}}
</style>
<div class="cm-footer">
    <div class="cm-footer-left">
        <span class="cm-footer-mark">&#9878;</span>
        <div>
            <div class="cm-footer-mark" style="font-size:0.9rem;">Issued by ComplianceMind</div>
            <div class="cm-footer-tag">Cited compliance check &middot; not legal advice</div>
        </div>
    </div>
    <div class="cm-footer-meta">
        Generated on {date_str}<br>
        Statutes reviewed: DPDP &middot; IT Act &middot; CPA &middot; GST
    </div>
</div>
"""


def _today_ist() -> str:
    """Return today's date in Asia/Kolkata (IST), formatted as
    '22 June 2026' — official style.

    BUGFIX: original used datetime.date.today() which returns the UTC date,
    not IST. Since the product is about Indian law and the footer reads as
    an official communication, the date should be the Indian calendar date.
    At UTC 19:00 (after 18:30), the date in India has already rolled over
    but date.today() would still return yesterday.
    """
    import datetime
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        ist_now = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        return ist_now.strftime("%d %B %Y")
    except Exception:
        # Fallback for environments without zoneinfo (e.g. older Python
        # without tzdata installed) — IST is UTC+5:30.
        utc_now = datetime.datetime.utcnow()
        ist_now = utc_now + datetime.timedelta(hours=5, minutes=30)
        return ist_now.strftime("%d %B %Y")


def estimate_cards_height(sources: list[dict]) -> int:
    """Estimate the rendered pixel height of the finding-cards block.

    WHY THIS EXISTS:
    streamlit.components.v1.html() takes a FIXED integer `height` argument.
    Unlike custom declare_component() components, html() does NOT support
    auto-resize via postMessage — any 'streamlit:setFrameHeight' messages
    we send from inside the iframe are silently ignored by the host.

    That means we MUST compute an accurate height up-front, otherwise
    long statute texts (the corpus has sections up to ~6700 chars) get
    silently clipped. With the original `len(sources) * 220` formula,
    a 4-source result with the CPA Section 2(47) text would render at
    ~3446px but get clipped to 880px — losing 75% of the cards.

    Calculation:
      Per card:
        - 22px top padding + 22px bottom padding = 44px
        - card-top (tag + status pill): ~28px including margin
        - h4 (act name): one line ~22px (line-height 1.3 × 17px font)
        - subtitle (title): ~21px (line-height 1.5 × 14px font) + 10px margin
        - body (statute text): ceil(text_len / 90) lines × 22px line-height
        = 130px fixed + body_height
      Container:
        - 4px top + 20px bottom padding (.cm-grid)
        - 18px gap between cards
        - +40px safety margin for font-rendering variance and the
          IntersectionObserver reveal animation
    """
    if not sources:
        return 120

    CHARS_PER_LINE = 90      # at 13.6px font, ~660px content width
    LINE_HEIGHT_PX = 22      # 0.85rem × 1.62 line-height
    CARD_FIXED_PX = 130      # padding + tag + h4 + subtitle + margins
    GAP_PX = 18
    CONTAINER_PAD_PX = 30
    SAFETY_PX = 60           # font-rendering variance + animation buffer

    total = CONTAINER_PAD_PX
    for src in sources:
        text_len = len(src.get("text", "") or "")
        body_lines = max(1, (text_len // CHARS_PER_LINE) + 1)
        card_h = CARD_FIXED_PX + body_lines * LINE_HEIGHT_PX
        total += card_h + GAP_PX

    return total + SAFETY_PX
