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

# ── Severity colors for findings (critical/major/minor) ────────────────────
# These are used for the severity badge on each finding card, and for the
# score breakdown in the notice header.
_SEVERITY_COLORS = {
    "critical": SEAL_RED,         # same as gap — critical gaps are the worst
    "major": "#C97A1D",           # a distinct orange-rust, between red and gold
    "minor": GOLD,                # mild — gold
}

_SEVERITY_LABELS = {
    "critical": "CRITICAL",
    "major": "MAJOR",
    "minor": "MINOR",
}

# ── Role colors (who in the org should care) ────────────────────────────────
# Each role gets a distinct muted color so role tags are scannable at a glance.
_ROLE_COLORS = {
    "Founder":    "#1B2A4A",   # navy — strategic
    "Legal":      "#8C1D1D",   # seal red — legal review
    "Engineering":"#4C6B3F",   # green — technical
    "DPO":        "#B08D57",   # gold — privacy
    "Finance":    "#C97A1D",   # orange — money
}

# ── Citation trust colors ───────────────────────────────────────────────────
_TRUST_COLORS = {
    "direct": COMPLIANT_GREEN,    # green — section directly addresses it
    "inferred": GOLD,             # gold — LLM reasoned by analogy
}
_TRUST_LABELS = {
    "direct": "DIRECT MATCH",
    "inferred": "INFERRED",
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

/* ════════════════════════════════════════════════════════════════════════
   ISSUE 1 FIX — Uniform-height preset buttons
   ════════════════════════════════════════════════════════════════════════
   Problem: The "D2C E-commerce" label wraps to two lines, making its
   button taller than the other four preset buttons, breaking visual
   consistency across the st.columns() row.

   Fix: give every preset button a fixed height + vertically-center the
   label so wrapping buttons (if any) don't push taller than the rest.
   We scope this to the row that immediately follows a paragraph whose
   text starts with "Quick start" — that way the styles ONLY affect the
   preset buttons and not other stButton instances on the page.

   Implementation: use :has() to find the column container that holds
   the preset buttons. Each preset button is rendered inside a column
   (div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]).
   We target buttons inside those columns by matching the preceding
   "Quick start" paragraph via the general sibling combinator.
   */

/* Step 1 — mark the preset row container. We do this by injecting a
   hidden div via st.markdown() right before the columns; this CSS
   targets any .cm-preset-row that exists on the page. See app.py
   where we add <div class="cm-preset-row"></div> via st.markdown(). */
.cm-preset-row + [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {{
    height: 60px !important;
    min-height: 60px !important;
    /* Vertically center the label whether it's one or two lines */
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    /* Allow wrapping but constrain the height — the flex centering
       keeps the text vertically centered so a wrapped 2-line label
       sits at the same vertical position as a 1-line label. */
    white-space: normal !important;
    line-height: 1.2 !important;
    padding: 6px 10px !important;
    /* Slightly smaller font so even the longest label fits without
       wrapping on most viewports; falls back to wrapping gracefully. */
    font-size: 0.78rem !important;
    font-weight: 600;
    text-align: center;
    /* Override the primary-button navy background — presets are
       secondary actions, so use a softer outline style. */
    background: #FFFFFF !important;
    color: {NAVY} !important;
    border: 1px solid rgba(27,42,74,0.22) !important;
    box-shadow: {CARD_SHADOW} !important;
    transition: all 220ms {MOTION_EASE} !important;
}}
.cm-preset-row + [data-testid="stHorizontalBlock"] [data-testid="stButton"] button:hover {{
    background: rgba(27,42,74,0.06) !important;
    border-color: {NAVY} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(27,42,74,0.15) !important;
}}
.cm-preset-row + [data-testid="stHorizontalBlock"] [data-testid="stButton"] button:active {{
    transform: translateY(0) !important;
}}
/* Keyboard focus — keep gold ring consistent with the rest of the app */
.cm-preset-row + [data-testid="stHorizontalBlock"] [data-testid="stButton"] button:focus-visible {{
    outline: 2px solid {GOLD} !important;
    outline-offset: 2px !important;
}}

/* ════════════════════════════════════════════════════════════════════════
   ISSUE 2 FIX — Styled radio buttons (mode selector + view toggle)
   ════════════════════════════════════════════════════════════════════════
   Problem: st.radio() uses the browser's default radio dot, which
   doesn't match the navy/gold theme.

   Fix: hide the default radio input, restyle the label as a pill/tab
   button. Selected = navy fill + cream text; unselected = cream fill
   + navy text + thin border. Hovering an unselected option adds a
   subtle gold underline.

   Targets:
   - The mode selector ("Single check" vs "Compare two businesses")
   - The report view toggle ("Plain English" vs "Full statute text")
   Both are horizontal radios, so we can style them identically.
   */

/* The radio widget container */
[data-testid="stRadio"] {{
    /* Remove Streamlit's default inner padding so our pills can
       stretch edge-to-edge inside the row. */
    padding-top: 4px !important;
}}
/* The horizontal row of options — Streamlit renders this as a flex
   row of <label> elements, each wrapping a hidden radio input + a
   visible text span. */
[data-testid="stRadio"] [role="radiogroup"] {{
    display: flex !important;
    gap: 8px !important;
    flex-wrap: wrap !important;
}}
/* Each individual radio option = one pill */
[data-testid="stRadio"] [role="radiogroup"] label {{
    flex: 1 1 0 !important;
    min-width: 140px !important;
    /* Pill shape */
    border: 1.5px solid rgba(27,42,74,0.20) !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
    color: {NAVY} !important;
    padding: 10px 18px !important;
    margin: 0 !important;
    /* Typography */
    font-family: {FONT_BODY} !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    text-align: center !important;
    cursor: pointer !important;
    transition: all 220ms {MOTION_EASE} !important;
    /* Make the label itself the flex container so we can hide the
       native radio dot and center the text. */
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    position: relative !important;
    user-select: none !important;
}}
/* Hide the native radio input — we'll drive the selected state via
   the parent label's [aria-checked="true"] attribute, which
   Streamlit sets automatically when the option is selected. */
[data-testid="stRadio"] [role="radiogroup"] label input[type="radio"] {{
    position: absolute !important;
    opacity: 0 !important;
    width: 0 !important;
    height: 0 !important;
    pointer-events: none !important;
}}
/* Hide Streamlit's default radio dot visual (the circle that sits
   next to the label text). */
[data-testid="stRadio"] [role="radiogroup"] label [data-testid="stRadioLabel"] {{
    /* Streamlit wraps the visible text in this. We keep it but
       remove any default left padding that was making room for
       the radio dot. */
    padding-left: 0 !important;
}}
/* Selected state — navy fill + cream text + gold accent border */
[data-testid="stRadio"] [role="radiogroup"] label[aria-checked="true"] {{
    background: {NAVY} !important;
    color: {PAPER} !important;
    border-color: {NAVY} !important;
    box-shadow: 0 2px 8px rgba(27,42,74,0.25) !important;
    /* Add a thin gold underline as a visual "active tab" marker */
    border-bottom: 3px solid {GOLD} !important;
}}
/* Unselected hover — subtle navy tint + gold underline hint */
[data-testid="stRadio"] [role="radiogroup"] label:not([aria-checked="true"]):hover {{
    background: rgba(27,42,74,0.04) !important;
    border-color: rgba(27,42,74,0.40) !important;
    color: {NAVY} !important;
    border-bottom: 3px solid rgba(176,141,87,0.50) !important;
}}
/* Keyboard focus on the label (when navigating via Tab) */
[data-testid="stRadio"] [role="radiogroup"] label:focus-within {{
    outline: 2px solid {GOLD} !important;
    outline-offset: 2px !important;
}}
/* The visible text inside each pill — make sure it inherits the
   pill's color so selected (cream) and unselected (navy) text colors
   are correct. */
[data-testid="stRadio"] [role="radiogroup"] label [data-testid="stRadioLabel"],
[data-testid="stRadio"] [role="radiogroup"] label span {{
    color: inherit !important;
    font-weight: inherit !important;
}}
/* When selected, also tint any emoji/icon in the label gold for
   a subtle premium feel. */
[data-testid="stRadio"] [role="radiogroup"] label[aria-checked="true"] span {{
    color: {GOLD} !important;
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
def render_notice_header(
    findings: list[dict] | None = None,
    score: int | None = None,
    grade: str = "",
    grade_color: str = "",
    score_summary: str = "",
) -> str:
    """A formal 'NOTICE OF FINDINGS' masthead that sits above the report.

    Features:
      - Big circular score gauge (0-100) with letter grade inside, drawn
        purely in CSS (conic-gradient ring + center disc). The ring color
        reflects the grade.
      - Summary tally: total / gaps / unclear / compliant
      - One-line score summary from the pipeline
    """
    findings = findings or []
    counts = {"compliant": 0, "gap": 0, "unclear": 0}
    severity_counts = {"critical": 0, "major": 0, "minor": 0}
    for f in findings:
        s = (f.get("status") or "").lower()
        if s in counts:
            counts[s] += 1
        sev = (f.get("severity") or "minor").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    total = sum(counts.values())

    # Score gauge — only render if score is provided
    has_score = score is not None
    gauge_html = ""
    if has_score:
        # Clamp score for the conic-gradient degree calculation
        s_clamped = max(0, min(100, int(score)))
        ring_deg = s_clamped * 3.6  # 100 * 3.6 = 360
        ring_color = grade_color or NAVY
        grade = grade or "—"
        gauge_html = f"""
        <div class="cm-score-gauge" style="--ring-color:{ring_color}; --ring-deg:{ring_deg}deg;">
            <div class="cm-score-inner">
                <span class="cm-score-num">{s_clamped}</span>
                <span class="cm-score-grade" style="color:{ring_color}">{grade}</span>
            </div>
            <span class="cm-score-label">Compliance Score</span>
        </div>
        """

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
.cm-notice-body {{
    display: flex;
    gap: 28px;
    align-items: flex-start;
}}
.cm-notice-text {{
    flex: 1;
    min-width: 0;
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
    margin: 0 0 8px 0;
    max-width: 52ch;
    line-height: 1.5;
}}
.cm-score-summary {{
    font-family: {FONT_MONO};
    font-size: 0.72rem;
    color: {NAVY};
    background: rgba(27,42,74,0.05);
    border-left: 3px solid {GOLD};
    padding: 6px 10px;
    margin: 8px 0 0 0;
    line-height: 1.4;
    border-radius: 0 4px 4px 0;
}}

/* ── Score gauge — pure CSS conic-gradient ring ────────────────────────
   The ring fills clockwise from 12 o'clock based on the score (0-100).
   Inner disc is ivory to match the page background, with the score number
   in display serif and the grade letter below it. */
.cm-score-gauge {{
    flex: 0 0 auto;
    width: 110px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    position: relative;
    padding: 4px 0;
}}
.cm-score-gauge::before {{
    content: "";
    width: 96px;
    height: 96px;
    border-radius: 50%;
    /* Conic gradient: filled arc in ring-color, remaining in light grey */
    background: conic-gradient(
        var(--ring-color) 0deg var(--ring-deg),
        rgba(27,42,74,0.10) var(--ring-deg) 360deg
    );
    display: block;
    position: relative;
}}
.cm-score-inner {{
    position: absolute;
    top: 4px;
    left: 50%;
    transform: translateX(-50%);
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.04);
}}
.cm-score-num {{
    font-family: {FONT_DISPLAY};
    font-size: 1.7rem;
    font-weight: 700;
    color: {NAVY};
    line-height: 1;
}}
.cm-score-grade {{
    font-family: {FONT_MONO};
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin-top: 2px;
}}
.cm-score-label {{
    font-family: {FONT_MONO};
    font-size: 0.56rem;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: {INK};
    opacity: 0.6;
    text-align: center;
}}

.cm-notice-tally {{
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    padding-top: 12px;
    margin-top: 14px;
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
.cm-tally-num.is-critical {{ color: {SEAL_RED}; }}
.cm-tally-num.is-major {{ color: #C97A1D; }}
.cm-tally-num.is-minor {{ color: {GOLD}; }}
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
@media (max-width: 520px) {{
    .cm-notice-body {{ flex-direction: column; align-items: center; }}
    .cm-notice-text {{ text-align: center; }}
    .cm-score-summary {{ text-align: left; }}
}}
</style>

<div class="cm-notice">
    <div class="cm-notice-body">
        {gauge_html if has_score else ''}
        <div class="cm-notice-text">
            <div class="cm-notice-eyebrow">Official Communication</div>
            <h2 class="cm-notice-title">Notice of Findings</h2>
            <p class="cm-notice-sub">The following compliance assessment has been
               prepared from the business description you submitted. Each finding
               is grounded in a specific provision of Indian statute law.</p>
            {f'<p class="cm-score-summary">{html.escape(score_summary)}</p>' if score_summary else ''}
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
                {f'''<div class="cm-tally-item">
                    <span class="cm-tally-num is-critical">{severity_counts['critical']}</span>
                    <span class="cm-tally-label">Critical</span>
                </div>''' if severity_counts['critical'] else ''}
                {f'''<div class="cm-tally-item">
                    <span class="cm-tally-num is-major">{severity_counts['major']}</span>
                    <span class="cm-tally-label">Major</span>
                </div>''' if severity_counts['major'] else ''}
            </div>
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
        (f.get("act"), f.get("section")): f for f in findings
    }

    cards_html = []
    for i, src in enumerate(sources):
        act = html.escape(src.get("act", ""))
        section = html.escape(src.get("section", ""))
        title = html.escape(src.get("title", ""))
        text = html.escape(src.get("text", ""))
        finding = status_by_section.get((src.get("act"), src.get("section"))) or {}
        status = finding.get("status")
        severity = (finding.get("severity") or "minor").lower()
        penalty_range = finding.get("penalty_range") or "Not specified in section"
        citation_trust = (finding.get("citation_trust") or "inferred").lower()
        role = finding.get("role") or "Founder"
        enforcement_trigger = finding.get("enforcement_trigger") or "Immediate"

        status_color = _STATUS_COLORS.get(status, GOLD) if status else GOLD
        status_label = html.escape(_status_label(status)) if status else ""
        severity_color = _SEVERITY_COLORS.get(severity, GOLD)
        severity_label = _SEVERITY_LABELS.get(severity, severity.upper())
        trust_color = _TRUST_COLORS.get(citation_trust, GOLD)
        trust_label = _TRUST_LABELS.get(citation_trust, "INFERRED")
        role_color = _ROLE_COLORS.get(role, NAVY)
        act_abbr = html.escape(_act_abbreviation(src.get("act", "")))

        delay_ms = i * 90  # staggered reveal across cards

        # Build the badge row: section tag + status pill + severity pill + trust badge
        badges = f'<span class="cm-tag">{section}</span>'
        if status_label:
            badges += f'<span class="cm-status" style="--status-color:{status_color}">{status_label}</span>'
            badges += f'<span class="cm-severity" style="--sev-color:{severity_color}">{severity_label}</span>'
            badges += f'<span class="cm-trust" style="--trust-color:{trust_color}">{trust_label}</span>'

        # Meta row: role tag + enforcement trigger
        meta_row = f"""
        <div class="cm-meta-row">
            <span class="cm-role" style="--role-color:{role_color}">👤 {html.escape(role)}</span>
            <span class="cm-trigger">⏱ {html.escape(enforcement_trigger)}</span>
        </div>
        """

        # Penalty row — only show if there's an actual penalty mentioned
        penalty_html = ""
        if penalty_range and penalty_range != "Not specified in section":
            penalty_html = f"""
            <div class="cm-penalty">
                <span class="cm-penalty-label">Penalty exposure:</span>
                <span class="cm-penalty-value">{html.escape(penalty_range)}</span>
            </div>
            """

        cards_html.append(f"""
        <article class="cm-card" data-cm-delay="{delay_ms}">
            <div class="cm-card-top">
                {badges}
            </div>
            <h4>{act}</h4>
            <p class="cm-card-subtitle"><strong>{title}</strong></p>
            {meta_row}
            <p class="cm-card-body">{text}</p>
            {penalty_html}
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
.cm-severity {{
    font-family: {FONT_MONO};
    font-size: 0.58rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--sev-color);
    padding: 3px 8px;
    background: color-mix(in srgb, var(--sev-color) 10%, transparent);
    border-radius: 4px;
    /* No border — severity is a secondary badge, lighter visual weight
       than the status pill. */
}}
/* Fallback for browsers without color-mix (older Safari) —
   use a semi-transparent overlay via box-shadow inset. */
@supports not (background: color-mix(in srgb, red 10%, transparent)) {{
    .cm-severity {{
        background: rgba(140, 29, 29, 0.08);
    }}
}}
.cm-penalty {{
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(140, 29, 29, 0.04);
    border-left: 3px solid {SEAL_RED};
    border-radius: 0 4px 4px 0;
    font-family: {FONT_MONO};
    font-size: 0.72rem;
    line-height: 1.4;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: baseline;
}}
.cm-penalty-label {{
    color: {INK};
    opacity: 0.55;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.cm-penalty-value {{
    color: {SEAL_RED};
    font-weight: 600;
}}
/* Citation trust badge — small, secondary visual weight */
.cm-trust {{
    font-family: {FONT_MONO};
    font-size: 0.54rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--trust-color);
    padding: 2px 6px;
    border: 1px dotted var(--trust-color);
    border-radius: 3px;
    opacity: 0.85;
}}
/* Meta row: role tag + enforcement trigger, sits between subtitle and body */
.cm-meta-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 0 0 8px 0;
    align-items: center;
}}
.cm-role {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    font-weight: 600;
    color: var(--role-color);
    padding: 2px 8px;
    background: color-mix(in srgb, var(--role-color) 8%, transparent);
    border-radius: 10px;
    white-space: nowrap;
}}
@supports not (background: color-mix(in srgb, red 10%, transparent)) {{
    .cm-role {{ background: rgba(27,42,74,0.06); }}
}}
.cm-trigger {{
    font-family: {FONT_MONO};
    font-size: 0.6rem;
    color: {INK};
    opacity: 0.6;
    white-space: nowrap;
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


def estimate_cards_height(sources: list[dict], findings: list[dict] | None = None) -> int:
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
        - card-top (tag + status pill + severity pill): ~28px including margin
        - h4 (act name): one line ~22px (line-height 1.3 × 17px font)
        - subtitle (title): ~21px (line-height 1.5 × 14px font) + 10px margin
        - body (statute text): ceil(text_len / 90) lines × 22px line-height
        - penalty row (if present): ~36px (8px padding × 2 + ~14px text + 10px margin)
        = ~130px fixed + body_height + (36 if penalty else 0)
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
    CARD_FIXED_PX = 160      # padding + tag + h4 + subtitle + meta row + margins
    PENALTY_ROW_PX = 50      # penalty row including margin + padding
    GAP_PX = 18
    CONTAINER_PAD_PX = 30
    SAFETY_PX = 80           # font-rendering variance + animation buffer

    # Build a lookup of (act, section) -> finding so we can check which
    # cards will have a penalty row.
    findings = findings or []
    finding_by_section = {
        (f.get("act"), f.get("section")): f for f in findings
    }

    total = CONTAINER_PAD_PX
    for src in sources:
        text_len = len(src.get("text", "") or "")
        body_lines = max(1, (text_len // CHARS_PER_LINE) + 1)
        card_h = CARD_FIXED_PX + body_lines * LINE_HEIGHT_PX

        # Add space for the penalty row if this card has a non-empty penalty
        finding = finding_by_section.get((src.get("act"), src.get("section"))) or {}
        penalty = finding.get("penalty_range") or ""
        if penalty and penalty != "Not specified in section":
            card_h += PENALTY_ROW_PX

        total += card_h + GAP_PX

    return total + SAFETY_PX


# ============================================================================
# 6. Risk timeline — when each finding becomes a problem
# ============================================================================
def render_timeline(findings: list[dict]) -> str:
    """Render a horizontal timeline of enforcement triggers.

    Each finding becomes a node on the timeline. Critical gaps get red nodes,
    major get orange, minor/compliant get gold/green. The node label shows
    the enforcement trigger phrase (e.g. "Immediate", "At Rs. 20L turnover").
    """
    if not findings:
        return ""

    # Deduplicate triggers — multiple findings with the same trigger
    # collapse into a single node.
    nodes = []
    seen_triggers = set()
    for f in findings:
        trigger = f.get("enforcement_trigger") or "Immediate"
        if trigger in seen_triggers:
            # Find existing node and append this finding's section
            for n in nodes:
                if n["trigger"] == trigger:
                    n["sections"].append(f.get("section", ""))
                    n["findings"].append(f)
                    break
        else:
            seen_triggers.add(trigger)
            nodes.append({
                "trigger": trigger,
                "sections": [f.get("section", "")],
                "findings": [f],
            })

    # Build node HTML
    nodes_html = []
    for i, node in enumerate(nodes):
        # Use the worst severity among the findings at this node
        severities = [(f.get("severity") or "minor").lower() for f in node["findings"]]
        if "critical" in severities:
            color = SEAL_RED
        elif "major" in severities:
            color = "#C97A1D"
        else:
            color = GOLD

        # Check if any finding is a gap
        statuses = [(f.get("status") or "").lower() for f in node["findings"]]
        is_gap = "gap" in statuses

        sections_str = ", ".join(node["sections"][:3])
        if len(node["sections"]) > 3:
            sections_str += f" +{len(node['sections']) - 3}"

        nodes_html.append(f"""
        <div class="cm-tl-node" style="--node-color:{color}">
            <div class="cm-tl-dot {'cm-tl-dot-gap' if is_gap else ''}"></div>
            <div class="cm-tl-label">{html.escape(node['trigger'])}</div>
            <div class="cm-tl-sections">{html.escape(sections_str)}</div>
        </div>
        """)

    nodes_markup = '<div class="cm-tl-line"></div>\n' + "\n".join(nodes_html)

    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-timeline {{
    font-family: {FONT_BODY};
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.10);
    border-radius: {CARD_RADIUS};
    box-shadow: {CARD_SHADOW};
    padding: 20px 22px;
    margin: 6px 0 18px 0;
}}
.cm-tl-title {{
    font-family: {FONT_DISPLAY};
    font-weight: 600;
    font-size: 1.05rem;
    color: {NAVY};
    margin: 0 0 4px 0;
}}
.cm-tl-sub {{
    font-family: {FONT_BODY};
    font-size: 0.82rem;
    color: {INK};
    opacity: 0.65;
    margin: 0 0 18px 0;
}}
.cm-tl-track {{
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
    padding: 20px 0 10px 0;
    overflow-x: auto;
}}
.cm-tl-line {{
    position: absolute;
    top: 28px;
    left: 5%;
    right: 5%;
    height: 2px;
    background: linear-gradient(90deg, {SEAL_RED}, {GOLD}, {COMPLIANT_GREEN});
    opacity: 0.3;
    z-index: 0;
}}
.cm-tl-node {{
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    min-width: 90px;
    flex: 1;
}}
.cm-tl-dot {{
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--node-color);
    border: 3px solid #FFFFFF;
    box-shadow: 0 0 0 1px var(--node-color);
    margin-bottom: 4px;
}}
.cm-tl-dot-gap {{
    box-shadow: 0 0 0 1px var(--node-color), 0 0 0 5px color-mix(in srgb, var(--node-color) 20%, transparent);
}}
@supports not (background: color-mix(in srgb, red 10%, transparent)) {{
    .cm-tl-dot-gap {{ box-shadow: 0 0 0 1px var(--node-color), 0 0 0 5px rgba(140,29,29,0.2); }}
}}
.cm-tl-label {{
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    font-weight: 600;
    color: {NAVY};
    text-align: center;
    line-height: 1.3;
}}
.cm-tl-sections {{
    font-family: {FONT_MONO};
    font-size: 0.55rem;
    color: {INK};
    opacity: 0.55;
    text-align: center;
    line-height: 1.3;
}}
.cm-tl-legend {{
    display: flex;
    gap: 16px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px dashed {RULE_GREY};
    font-family: {FONT_MONO};
    font-size: 0.58rem;
    color: {INK};
    opacity: 0.65;
    flex-wrap: wrap;
}}
.cm-tl-legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
}}
.cm-tl-legend-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}}
</style>

<div class="cm-timeline">
    <h3 class="cm-tl-title">⏱  Risk Timeline — When Each Rule Bites</h3>
    <p class="cm-tl-sub">Each node shows when the finding's enforcement trigger
       fires. Larger rings indicate active gaps that need attention.</p>
    <div class="cm-tl-track">
        {nodes_markup}
    </div>
    <div class="cm-tl-legend">
        <span class="cm-tl-legend-item"><span class="cm-tl-legend-dot" style="background:{SEAL_RED}"></span> Critical</span>
        <span class="cm-tl-legend-item"><span class="cm-tl-legend-dot" style="background:#C97A1D"></span> Major</span>
        <span class="cm-tl-legend-item"><span class="cm-tl-legend-dot" style="background:{GOLD}"></span> Minor / Compliant</span>
        <span class="cm-tl-legend-item">Ring = active gap</span>
    </div>
</div>
"""


# ============================================================================
# 7. Comparison view — two results side-by-side
# ============================================================================
def render_comparison(score_a: int, grade_a: str, grade_color_a: str,
                      score_b: int, grade_b: str, grade_color_b: str,
                      label_a: str = "A", label_b: str = "B",
                      findings_a: list[dict] | None = None,
                      findings_b: list[dict] | None = None) -> str:
    """Render a side-by-side comparison of two compliance check results.

    Shows two score gauges and a per-status diff table so the user can
    see which option has more gaps / critical issues.
    """
    findings_a = findings_a or []
    findings_b = findings_b or []

    def _counts(findings):
        c = {"gap": 0, "unclear": 0, "compliant": 0, "critical": 0, "major": 0}
        for f in findings:
            s = (f.get("status") or "").lower()
            sev = (f.get("severity") or "minor").lower()
            if s in c:
                c[s] += 1
            if sev in ("critical", "major"):
                c[sev] += 1
        return c

    ca = _counts(findings_a)
    cb = _counts(findings_b)

    def _gauge(score, grade, color, label):
        s = max(0, min(100, int(score)))
        deg = s * 3.6
        return f"""
        <div class="cm-cmp-card">
            <div class="cm-cmp-label">{html.escape(label)}</div>
            <div class="cm-cmp-gauge" style="--ring-color:{color}; --ring-deg:{deg}deg;">
                <div class="cm-cmp-gauge-inner">
                    <span class="cm-cmp-score">{s}</span>
                    <span class="cm-cmp-grade" style="color:{color}">{grade}</span>
                </div>
            </div>
            <div class="cm-cmp-stats">
                <div><span class="cm-cmp-stat-num" style="color:{SEAL_RED}">{ca['gap'] if label == label_a else cb['gap']}</span> gaps</div>
                <div><span class="cm-cmp-stat-num" style="color:{SEAL_RED}">{ca['critical'] if label == label_a else cb['critical']}</span> critical</div>
                <div><span class="cm-cmp-stat-num" style="color:{COMPLIANT_GREEN}">{ca['compliant'] if label == label_a else cb['compliant']}</span> compliant</div>
            </div>
        </div>
        """

    gauge_a = _gauge(score_a, grade_a, grade_color_a, label_a)
    gauge_b = _gauge(score_b, grade_b, grade_color_b, label_b)

    # Determine winner
    if score_a > score_b:
        verdict = f"{label_a} wins (+{score_a - score_b} points)"
        verdict_color = COMPLIANT_GREEN
    elif score_b > score_a:
        verdict = f"{label_b} wins (+{score_b - score_a} points)"
        verdict_color = COMPLIANT_GREEN
    else:
        verdict = "Tie — same compliance score"
        verdict_color = GOLD

    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-comparison {{
    font-family: {FONT_BODY};
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.10);
    border-radius: {CARD_RADIUS};
    box-shadow: {CARD_SHADOW};
    padding: 22px 26px;
    margin: 6px 0 18px 0;
}}
.cm-cmp-title {{
    font-family: {FONT_DISPLAY};
    font-weight: 700;
    font-size: 1.3rem;
    color: {NAVY};
    margin: 0 0 4px 0;
    text-align: center;
}}
.cm-cmp-verdict {{
    font-family: {FONT_MONO};
    font-size: 0.78rem;
    font-weight: 600;
    color: {verdict_color};
    text-align: center;
    margin: 0 0 20px 0;
    padding: 6px 12px;
    background: color-mix(in srgb, {verdict_color} 8%, transparent);
    border-radius: 6px;
    display: inline-block;
    width: 100%;
}}
@supports not (background: color-mix(in srgb, red 10%, transparent)) {{
    .cm-cmp-verdict {{ background: rgba(76,107,63,0.08); }}
}}
.cm-cmp-row {{
    display: flex;
    gap: 20px;
    align-items: stretch;
}}
.cm-cmp-card {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 16px;
    border: 1px solid rgba(27,42,74,0.10);
    border-radius: 10px;
    background: {PAPER};
}}
.cm-cmp-label {{
    font-family: {FONT_MONO};
    font-size: 0.72rem;
    font-weight: 700;
    color: {NAVY};
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
.cm-cmp-gauge {{
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: conic-gradient(
        var(--ring-color) 0deg var(--ring-deg),
        rgba(27,42,74,0.10) var(--ring-deg) 360deg
    );
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}
.cm-cmp-gauge-inner {{
    width: 68px;
    height: 68px;
    border-radius: 50%;
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.08);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}}
.cm-cmp-score {{
    font-family: {FONT_DISPLAY};
    font-size: 1.5rem;
    font-weight: 700;
    color: {NAVY};
    line-height: 1;
}}
.cm-cmp-grade {{
    font-family: {FONT_MONO};
    font-size: 0.65rem;
    font-weight: 700;
    margin-top: 2px;
}}
.cm-cmp-stats {{
    display: flex;
    gap: 12px;
    font-family: {FONT_MONO};
    font-size: 0.62rem;
    color: {INK};
    opacity: 0.75;
    text-align: center;
}}
.cm-cmp-stats > div {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}
.cm-cmp-stat-num {{
    font-family: {FONT_DISPLAY};
    font-size: 1.1rem;
    font-weight: 700;
}}
@media (max-width: 520px) {{
    .cm-cmp-row {{ flex-direction: column; }}
}}
</style>

<div class="cm-comparison">
    <h3 class="cm-cmp-title">⚖️  Side-by-Side Comparison</h3>
    <div style="text-align:center;"><span class="cm-cmp-verdict">{verdict}</span></div>
    <div class="cm-cmp-row">
        {gauge_a}
        {gauge_b}
    </div>
</div>
"""


# ============================================================================
# 8. Action plan checklist — interactive gap-resolution tracker
# ============================================================================
def render_action_plan(findings: list[dict], resolved_keys: set | None = None) -> str:
    """Render an interactive action plan checklist.

    Each gap or unclear finding becomes a checklist item. When the user
    marks an item as resolved (via Streamlit checkboxes in app.py), the
    score is recalculated. This function just renders the visual list —
    the actual checkbox state is managed by Streamlit via st.session_state.
    """
    resolved_keys = resolved_keys or set()
    actionable = [f for f in findings
                  if (f.get("status") or "").lower() in ("gap", "unclear")]

    if not actionable:
        return f"""
<style>
.cm-actionplan {{
    font-family: {FONT_BODY};
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.10);
    border-left: 4px solid {COMPLIANT_GREEN};
    border-radius: {CARD_RADIUS};
    padding: 18px 22px;
    margin: 6px 0 18px 0;
}}
.cm-ap-title {{ font-family: {FONT_DISPLAY}; font-weight: 600; color: {NAVY}; margin: 0 0 4px 0; }}
.cm-ap-sub {{ font-size: 0.85rem; color: {INK}; opacity: 0.7; margin: 0; }}
</style>
<div class="cm-actionplan">
    <h3 class="cm-ap-title">✅  Action Plan — No Open Items</h3>
    <p class="cm-ap-sub">All reviewed sections are compliant. No action needed.</p>
</div>
"""

    items_html = []
    for f in actionable:
        status = (f.get("status") or "").lower()
        severity = (f.get("severity") or "minor").lower()
        key = f"{f.get('act', '')}::{f.get('section', '')}"
        is_resolved = key in resolved_keys

        if status == "gap":
            sev_color = _SEVERITY_COLORS.get(severity, GOLD)
            icon = "🔴" if severity == "critical" else "🟠" if severity == "major" else "🟡"
        else:  # unclear
            sev_color = GOLD
            icon = "❓"

        act_abbr = _act_abbreviation(f.get("act", ""))
        section = html.escape(f.get("section", ""))
        act = html.escape(f.get("act", ""))
        reasoning = html.escape(f.get("reasoning", ""))
        role = html.escape(f.get("role") or "Founder")

        checked_attr = "checked" if is_resolved else ""
        resolved_class = " cm-ap-resolved" if is_resolved else ""

        items_html.append(f"""
        <label class="cm-ap-item{resolved_class}" style="--sev-color:{sev_color}">
            <span class="cm-ap-icon">{icon}</span>
            <span class="cm-ap-check">
                <input type="checkbox" data-key="{html.escape(key)}" {checked_attr} disabled>
                <span class="cm-ap-box"></span>
            </span>
            <span class="cm-ap-content">
                <span class="cm-ap-section">{section} · {act}</span>
                <span class="cm-ap-reasoning">{reasoning}</span>
                <span class="cm-ap-meta">👤 {role}</span>
            </span>
            <span class="cm-ap-seal">{act_abbr}</span>
        </label>
        """)

    items_markup = "\n".join(items_html)
    total = len(actionable)
    resolved_count = len([f for f in actionable
                          if f"{f.get('act', '')}::{f.get('section', '')}" in resolved_keys])

    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
body {{ margin: 0; }}
.cm-actionplan {{
    font-family: {FONT_BODY};
    background: #FFFFFF;
    border: 1px solid rgba(27,42,74,0.10);
    border-left: 4px solid {NAVY};
    border-radius: {CARD_RADIUS};
    padding: 20px 22px;
    margin: 6px 0 18px 0;
}}
.cm-ap-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px dashed {RULE_GREY};
}}
.cm-ap-title {{
    font-family: {FONT_DISPLAY};
    font-weight: 600;
    font-size: 1.1rem;
    color: {NAVY};
    margin: 0;
}}
.cm-ap-progress {{
    font-family: {FONT_MONO};
    font-size: 0.72rem;
    color: {INK};
    opacity: 0.7;
}}
.cm-ap-progress strong {{
    color: {COMPLIANT_GREEN};
}}
.cm-ap-item {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 10px;
    border-radius: 8px;
    margin-bottom: 6px;
    cursor: default;
    transition: background 200ms ease;
    position: relative;
}}
.cm-ap-item:hover {{
    background: rgba(27,42,74,0.03);
}}
.cm-ap-item.cm-ap-resolved {{
    opacity: 0.5;
}}
.cm-ap-item.cm-ap-resolved .cm-ap-content {{
    text-decoration: line-through;
}}
.cm-ap-icon {{
    flex: 0 0 auto;
    font-size: 0.9rem;
    line-height: 1.5;
}}
.cm-ap-check {{
    flex: 0 0 auto;
    position: relative;
    width: 18px;
    height: 18px;
    margin-top: 2px;
}}
.cm-ap-check input {{
    position: absolute;
    opacity: 0;
    width: 100%;
    height: 100%;
    cursor: pointer;
    margin: 0;
}}
.cm-ap-box {{
    display: block;
    width: 18px;
    height: 18px;
    border: 2px solid var(--sev-color);
    border-radius: 4px;
    background: #FFFFFF;
    transition: all 200ms ease;
}}
.cm-ap-check input:checked + .cm-ap-box {{
    background: var(--sev-color);
    border-color: var(--sev-color);
}}
.cm-ap-check input:checked + .cm-ap-box::after {{
    content: "✓";
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
}}
.cm-ap-content {{
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}}
.cm-ap-section {{
    font-family: {FONT_MONO};
    font-size: 0.7rem;
    font-weight: 600;
    color: {NAVY};
}}
.cm-ap-reasoning {{
    font-size: 0.85rem;
    color: {INK};
    opacity: 0.85;
    line-height: 1.4;
}}
.cm-ap-meta {{
    font-family: {FONT_MONO};
    font-size: 0.58rem;
    color: {INK};
    opacity: 0.55;
    margin-top: 2px;
}}
.cm-ap-seal {{
    flex: 0 0 auto;
    font-family: {FONT_MONO};
    font-size: 0.55rem;
    font-weight: 700;
    color: {SEAL_RED};
    border: 1px solid {SEAL_RED};
    border-radius: 50%;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.6;
}}
</style>

<div class="cm-actionplan">
    <div class="cm-ap-header">
        <h3 class="cm-ap-title">📋  Action Plan — Resolve Your Gaps</h3>
        <span class="cm-ap-progress"><strong>{resolved_count}</strong> / {total} resolved</span>
    </div>
    {items_markup}
</div>
"""
