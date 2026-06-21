"""
ComplianceMind — "Government Gazette" design system.

Two delivery mechanisms, per the design brief:
  1. GLOBAL_CSS — injected once via st.markdown(unsafe_allow_html=True) to
     restyle Streamlit's native widgets (text area, button, expander, alerts)
     so they match the token system below.
  2. render_hero() / render_finding_cards() — self-contained HTML/CSS/JS
     strings rendered via streamlit.components.v1.html() for the decorative,
     scroll-animated elements that native CSS injection can't drive.

Design tokens are LOCKED per the brief — do not introduce new hex values.
"""

import html

# ── Phase 3: locked color tokens ────────────────────────────────────────────
PAPER = "#F7F5F0"        # background
INK = "#1A1A1A"           # primary text
NAVY = "#1B2A4A"          # primary accent (official navy)
SEAL_RED = "#8C1D1D"      # status/alert accent
GOLD = "#B08D57"          # secondary accent (emblem gold)
COMPLIANT_GREEN = "#4C6B3F"  # muted olive-green, chosen to harmonize with
                              # the navy/red/gold "ink on aged paper" palette
                              # rather than a generic bright green

# ── Phase 1 (fallback) motion + card tokens — see chat for rationale ───────
CARD_RADIUS = "16px"
CARD_SHADOW = "0 4px 20px rgba(26,26,26,0.08), 0 1px 3px rgba(26,26,26,0.04)"
CARD_BORDER = "1px solid rgba(26,26,26,0.07)"
MOTION_DURATION = "420ms"
MOTION_EASE = "cubic-bezier(0.16, 1, 0.3, 1)"  # soft "ease-out-expo" landing

FONT_DISPLAY = "'Source Serif 4', Georgia, serif"
FONT_BODY = "'IBM Plex Sans', -apple-system, sans-serif"
FONT_MONO = "'IBM Plex Mono', 'SFMono-Regular', monospace"

GOOGLE_FONTS_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&"
    "family=IBM+Plex+Sans:wght@400;500;600&"
    "family=IBM+Plex+Mono:wght@400;500&display=swap');"
)

_STATUS_COLORS = {
    "compliant": COMPLIANT_GREEN,
    "gap": SEAL_RED,
    "unclear": GOLD,
}


# ============================================================================
# 1. Global CSS — restyles Streamlit's own widgets
# ============================================================================
def get_global_css() -> str:
    return f"""
<style>
{GOOGLE_FONTS_IMPORT}

/* ── Top header / toolbar (the "Deploy" bar) ─────────────────────────────
   Unstyled, this defaults to Streamlit's own theme (often a stark black
   bar) regardless of our .stApp overrides below, since it's themed
   independently. Retint it to read as a quiet letterhead strip. */
header[data-testid="stHeader"] {{
    background: {PAPER} !important;
    border-bottom: 1px solid rgba(27,42,74,0.10);
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

.stApp {{
    background: {PAPER};
}}
.block-container {{
    max-width: 760px;
    padding-top: 1.5rem;
}}

/* ── Typography ───────────────────────────────────────────────────────── */
.stApp, .stApp p, .stApp li, .stApp label, .stMarkdown {{
    font-family: {FONT_BODY};
    color: {INK};
    line-height: 1.65;
}}
.stApp h1, .stApp h2, .stApp h3 {{
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

/* Native st.title()/st.caption() — kept as a quiet fallback; the visible
   header is the custom hero component below, so hide the default title to
   avoid a duplicate heading. */
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
    padding: 0.6rem 1.2rem;
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

/* ── Expander ─────────────────────────────────────────────────────────── */
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
    border-color: rgba(27,42,74,0.15) !important;
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
# 2. Hero banner — components.v1.html()
# ============================================================================
def render_hero() -> str:
    """Oversized display-serif hero with a CSS-drawn official emblem.
    No image asset — the seal is pure radial-gradient + border."""
    return f"""
<style>
{GOOGLE_FONTS_IMPORT}
* {{ box-sizing: border-box; }}
.cm-hero {{
    font-family: {FONT_BODY};
    background: {PAPER};
    padding: 8px 4px 28px 4px;
    display: flex;
    align-items: center;
    gap: 24px;
    opacity: 0;
    transform: translateY(18px);
    animation: cmHeroIn {MOTION_DURATION} {MOTION_EASE} forwards;
}}
@keyframes cmHeroIn {{
    to {{ opacity: 1; transform: translateY(0); }}
}}
.cm-emblem {{
    flex: 0 0 auto;
    width: 76px;
    height: 76px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #2a4068 0%, {NAVY} 55%, #142036 100%);
    border: 3px solid {GOLD};
    box-shadow: 0 4px 14px rgba(27,42,74,0.35), inset 0 0 0 3px rgba(247,245,240,0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}}
.cm-emblem::before {{
    content: "";
    position: absolute;
    inset: 8px;
    border-radius: 50%;
    border: 1px dashed rgba(247,245,240,0.4);
}}
.cm-emblem-glyph {{
    font-family: {FONT_DISPLAY};
    color: {PAPER};
    font-size: 28px;
    font-weight: 600;
    line-height: 1;
}}
.cm-hero-text h1 {{
    font-family: {FONT_DISPLAY};
    font-weight: 700;
    font-size: clamp(2.1rem, 5vw, 3rem);
    line-height: 1.05;
    letter-spacing: -0.015em;
    color: {NAVY};
    margin: 0 0 6px 0;
}}
.cm-hero-text p {{
    font-family: {FONT_BODY};
    font-size: 0.98rem;
    color: {INK};
    opacity: 0.72;
    margin: 0;
    max-width: 46ch;
}}
@media (prefers-reduced-motion: reduce) {{
    .cm-hero {{ animation: none; opacity: 1; transform: none; }}
}}
</style>

<div class="cm-hero">
    <div class="cm-emblem"><span class="cm-emblem-glyph">&#9878;</span></div>
    <div class="cm-hero-text">
        <h1>ComplianceMind</h1>
        <p>Describe your business in plain English and find out which Indian
           laws apply &mdash; with every claim cited to a real statute section.</p>
    </div>
</div>
"""


# ============================================================================
# 3. Finding / source cards — components.v1.html()
# ============================================================================
def _status_label(status: str) -> str:
    return {"compliant": "Compliant", "gap": "Gap found", "unclear": "Unclear"}.get(
        status, status.title() if status else ""
    )


def render_finding_cards(sources: list[dict], findings: list[dict] | None = None) -> str:
    """Render all source/finding cards as one animated HTML block.

    Each card fades + slides up as it scrolls into view, and carries a small
    CSS-drawn seal-red 'verified' stamp next to its citation that lands with
    the same entrance motion (slightly bouncier, to feel like a stamp).
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
        status_color = _STATUS_COLORS.get(status, GOLD)
        status_label = html.escape(_status_label(status)) if status else ""

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
            <div class="cm-stamp" aria-hidden="true">
                <div class="cm-stamp-ring">
                    <span class="cm-stamp-text">VERIFIED</span>
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
    gap: 20px;
    padding: 4px 2px 24px 2px;
}}
.cm-card {{
    position: relative;
    background: #FFFFFF;
    border-radius: {CARD_RADIUS};
    box-shadow: {CARD_SHADOW};
    border: {CARD_BORDER};
    padding: 22px 26px 22px 22px;
    opacity: 0;
    transform: translateY(24px);
    transition: opacity {MOTION_DURATION} {MOTION_EASE},
                transform {MOTION_DURATION} {MOTION_EASE},
                box-shadow 200ms ease;
}}
.cm-card:hover {{
    box-shadow: 0 8px 28px rgba(26,26,26,0.12), 0 2px 6px rgba(26,26,26,0.06);
}}
.cm-card.cm-visible {{
    opacity: 1;
    transform: translateY(0);
}}
.cm-card-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
}}
.cm-tag {{
    font-family: {FONT_MONO};
    font-size: 0.74rem;
    letter-spacing: 0.02em;
    background: rgba(27,42,74,0.08);
    color: {NAVY};
    padding: 3px 9px;
    border-radius: 5px;
}}
.cm-status {{
    font-family: {FONT_BODY};
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--status-color);
}}
.cm-status::before {{
    content: "\\25CF";
    margin-right: 5px;
    font-size: 0.6rem;
}}
.cm-card h4 {{
    font-family: {FONT_DISPLAY};
    color: {NAVY};
    font-weight: 600;
    font-size: 1.08rem;
    margin: 0 0 4px 0;
}}
.cm-card-subtitle {{
    margin: 0 0 8px 0;
    font-size: 0.9rem;
    color: {INK};
    opacity: 0.85;
}}
.cm-card-body {{
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.6;
    color: {INK};
    opacity: 0.78;
}}

/* Seal stamp — pure CSS, no image asset */
.cm-stamp {{
    position: absolute;
    top: 16px;
    right: 18px;
    opacity: 0;
    transform: scale(0.4) rotate(-30deg);
    transition: opacity {MOTION_DURATION} cubic-bezier(0.34, 1.56, 0.64, 1),
                transform {MOTION_DURATION} cubic-bezier(0.34, 1.56, 0.64, 1);
}}
.cm-card.cm-visible .cm-stamp {{
    opacity: 0.9;
    transform: scale(1) rotate(-8deg);
}}
.cm-stamp-ring {{
    width: 54px;
    height: 54px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #a8332f 0%, {SEAL_RED} 60%, #6e1414 100%);
    border: 2px solid {SEAL_RED};
    box-shadow: inset 0 0 0 3px rgba(247,245,240,0.55);
    display: flex;
    align-items: center;
    justify-content: center;
}}
.cm-stamp-text {{
    font-family: {FONT_MONO};
    font-size: 0.42rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: {PAPER};
    text-align: center;
}}
@media (prefers-reduced-motion: reduce) {{
    .cm-card, .cm-stamp {{ transition: none !important; }}
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

    if (reduceMotion) {{
        // Skip scroll/cross-frame machinery entirely — just show everything.
        cards.forEach(function(card) {{ card.classList.add('cm-visible'); }});
        return;
    }}

    function reveal(card) {{
        var delay = parseInt(card.getAttribute('data-cm-delay') || '0', 10);
        setTimeout(function() {{ card.classList.add('cm-visible'); }}, delay);
    }}

    // Try true scroll-linked reveal by reaching into the parent Streamlit
    // page (components.v1.html() iframes are same-origin via srcdoc).
    // Falls back to a staggered reveal-on-mount if cross-frame access is
    // blocked for any reason — never leaves cards stuck invisible.
    var usedCrossFrame = false;
    try {{
        var frameEl = window.frameElement;
        var parentWin = window.parent;
        if (frameEl && parentWin && parentWin !== window) {{
            usedCrossFrame = true;

            function checkVisible() {{
                var frameRect = frameEl.getBoundingClientRect();
                var vh = parentWin.innerHeight || 800;
                cards.forEach(function(card) {{
                    if (card.classList.contains('cm-visible')) return;
                    var cardRect = card.getBoundingClientRect();
                    var top = frameRect.top + cardRect.top;
                    if (top < vh * 0.9) {{
                        reveal(card);
                    }}
                }});
            }}

            parentWin.addEventListener('scroll', checkVisible, {{ passive: true }});
            parentWin.addEventListener('resize', checkVisible);
            checkVisible();
            setTimeout(checkVisible, 300); // catch late layout settle
        }}
    }} catch (err) {{
        usedCrossFrame = false;
    }}

    if (!usedCrossFrame) {{
        // Fallback: local IntersectionObserver (effectively reveal-on-mount
        // inside the component's own iframe), staggered per card.
        if ('IntersectionObserver' in window) {{
            var io = new IntersectionObserver(function(entries) {{
                entries.forEach(function(entry) {{
                    if (entry.isIntersecting) {{
                        reveal(entry.target);
                        io.unobserve(entry.target);
                    }}
                }});
            }}, {{ threshold: 0.15, rootMargin: "-10% 0px -10% 0px" }});
            cards.forEach(function(card) {{ io.observe(card); }});
        }} else {{
            cards.forEach(reveal);
        }}
    }}
}})();
</script>
"""
