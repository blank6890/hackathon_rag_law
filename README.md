# ComplianceMind — Government Gazette UI Redesign

Redesigned Streamlit UI for the hackathon_rag_law project, using a "government
gazette / official notice" visual language: ivory paper, ink black, official
navy, seal red, emblem gold. Each finding carries a CSS-drawn circular seal
stamp bearing the act abbreviation (DPDP / ITA / CPA / GST / ECOM) — visually
saying "this claim has been officially verified".

## Bugs fixed (vs original repo)

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `app.py` | `st.iframe()` does not exist in Streamlit — both calls would crash on launch | Replaced with `streamlit.components.v1.html()` |
| 2 | `app.py` | `height="content"` is invalid — `html()` requires an integer pixel height | Pass explicit integer heights; new `estimate_cards_height()` helper computes accurate height per card |
| 3 | `app.py` | Missing `streamlit.components.v1` import | Added `import streamlit.components.v1 as components` |
| 4 | `pipeline.py` | `_client = Groq()` at module import time crashes the app if `GROQ_API_KEY` is unset, before any UI loads | Lazy singleton via `_get_client()` — created on first LLM call |
| 5 | `pipeline.py` | Empty retrieval results would push the scoring LLM to hallucinate | Guard with a friendly "couldn't find relevant statutes" clarification message |
| 6 | `pipeline.py` | Clarification logic checked `is None` on boolean fields — never triggered | Now driven by `is_vague` flag + empty string/list checks |
| 7 | `styles.py` | `_today_ist()` was misnamed — returned UTC date, not IST (product is about Indian law; at UTC 19:00 the Indian date has already rolled over) | Now uses `zoneinfo.ZoneInfo("Asia/Kolkata")` with a UTC+5:30 fallback |
| 8 | `app.py` + `styles.py` | **Finding cards silently clipped** — old `len(sources) * 220` formula gave 880px for a 4-source result, but real content with the 6727-char CPA Section 2(47) text renders at ~3446px. **75% of cards were invisible.** | New `estimate_cards_height(sources)` computes per-card height based on actual text length (chars-per-line × line-height × lines + fixed overhead). Plus `scrolling=True` as a safety net. |
| 9 | `styles.py` | `render_finding_cards()` sent `postMessage('streamlit:setFrameHeight')` to the parent — but that protocol only works for custom `declare_component()` components, NOT for `components.html()`. Messages were silently ignored. | Removed the misleading JS. Height is now set correctly up-front via `estimate_cards_height()`. |
| 10 | `styles.py` | `render_footer()` used a fragile `.replace('{date}', _today_ist())` pattern that worked but was obscure and would break if the date string ever contained `{` or `}` | Direct f-string interpolation: `Generated on {date_str}` |

## How to run

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your-key-here"
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## Design system

| Token | Value | Used for |
|-------|-------|----------|
| `PAPER` | `#F7F5F0` | ivory page background |
| `INK` | `#1A1A1A` | body text |
| `NAVY` | `#1B2A4A` | headings, primary button, accent text |
| `SEAL_RED` | `#8C1D1D` | "gap" status, seal stamps |
| `GOLD` | `#B08D57` | emblem rim, "unclear" status, accent rules |
| `COMPLIANT_GREEN` | `#4C6B3F` | "compliant" status |

**Typography:**
- Display: Source Serif 4 (with Lora fallback) — headings, masthead, seal text
- Body: IBM Plex Sans — UI text, descriptions
- Mono: IBM Plex Mono — citations, reference numbers, status pills

**Custom components** (rendered via `components.v1.html()`):
- `render_hero()` — letterhead masthead with file-reference number, CSS-drawn
  emblem (layered radial gradient + gold rim + dashed inner ring), and tagline
- `render_notice_header(findings)` — "NOTICE OF FINDINGS" masthead with live
  tally of total / gaps / unclear / compliant counts
- `render_finding_cards(sources, findings)` — per-finding cards with status
  pills and CSS-drawn seal stamps bearing the act abbreviation; staggered
  scroll-triggered reveal via IntersectionObserver. Iframe height is computed
  up-front by `estimate_cards_height(sources)` based on actual text length
  per card (see bug fix #8 — `components.html()` doesn't support
  postMessage auto-resize, so the height must be calculated server-side)
- `render_footer()` — "Issued by ComplianceMind" signature block with
  IST date (bug fix #7 — uses `Asia/Kolkata` timezone, not UTC)
