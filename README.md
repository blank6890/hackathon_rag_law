# ComplianceMind — Government Gazette UI

Redesigned Streamlit UI for the hackathon_rag_law project, using a "government
gazette / official notice" visual language: ivory paper, ink black, official
navy, seal red, emblem gold. Each finding carries a CSS-drawn circular seal
stamp bearing the act abbreviation (DPDP / ITA / CPA / GST / ECOM) — visually
saying "this claim has been officially verified".

## Features

### All Tier 1 + 2 features (v4)

#### Tier 1 — High impact
1. **Compliance Score (0–100) with letter grade** — CSS conic-gradient gauge.
   Formula: `100 - 25×critical_gaps - 12×major_gaps - 5×minor_gaps - 3×unclear`
2. **Before/After Action Plan** — interactive checklist where each gap/unclear
   finding becomes a checkbox. As you check items off, the score recalculates
   live (resolved gaps are treated as compliant).
3. **PDF certificate download** — exports the whole notice as a PDF matching
   the gazette aesthetic (ReportLab, ivory background, score gauge as a
   colored ring).
4. **Plain-English ↔ Legalese toggle** — radio toggle at the top of the
   report. "Plain English" shows the LLM's summary; "Full statute text"
   shows the actual section text in `st.info` boxes.
5. **Comparison mode** — toggle to "Compare two businesses", enter two
   descriptions side-by-side, get two score gauges + a verdict showing
   which wins and by how many points.
6. **Industry presets** — 5 one-click templates (EdTech, Fintech UPI,
   D2C E-commerce, Health App, SaaS B2B).
7. **Risk timeline** — horizontal timeline with a node per enforcement
   trigger. Critical/major/minor nodes are colored red/orange/gold; active
   gaps get a larger ring.

#### Tier 2 — Polish & depth
8. **Citation trust score** — each finding is tagged "DIRECT MATCH" (the
   section text directly addresses the business's situation) or "INFERRED"
   (LLM reasoned by analogy). Shown as a dotted-border badge on each card.
9. **Ask-a-follow-up chat** — after the report, a `st.chat_input` box
   lets the user ask questions grounded in the same findings/sources.
   Uses `answer_followup()` in pipeline.py.
10. **History sidebar** — `st.session_state.history` stores the last 10
    checks (description, score, grade, timestamp). Click any item to reload.
11. **Multilingual notice** — sidebar language picker (English / Hindi /
    Tamil / Bengali). Calls `translate_report()` which uses Groq to
    translate the markdown report while keeping act names + citations
    in English.
12. **Severity weights + cost estimator** — each finding has
    `critical`/`major`/`minor` severity + `penalty_range` extracted from
    the statute text (e.g. "Up to Rs. 250 crore penalty").
13. **Real ChromaDB retrieval** — semantic search via `all-MiniLM-L6-v2`
    embeddings. Corpus auto-loads on first use.
14. **Role tags** — each finding is tagged with who should care:
    Founder / Legal / Engineering / DPO / Finance. Shown as a colored
    pill with 👤 icon.
15. **Shareable URL** — sidebar shows a `?q=<encoded_desc>` query string
    for the last check. On load, the app checks `st.query_params` for a
    `q` param and pre-fills the textarea.

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
| 8 | `app.py` + `styles.py` | **Finding cards silently clipped** — old `len(sources) * 220` formula gave 880px for a 4-source result, but real content with the 6727-char CPA Section 2(47) text renders at ~3446px. **75% of cards were invisible.** | New `estimate_cards_height(sources, findings)` computes per-card height based on actual text length + penalty rows. Plus `scrolling=True` as a safety net. |
| 9 | `styles.py` | `render_finding_cards()` sent `postMessage('streamlit:setFrameHeight')` to the parent — but that protocol only works for custom `declare_component()` components, NOT for `components.html()`. Messages were silently ignored. | Removed the misleading JS. Height is now set correctly up-front via `estimate_cards_height()`. |
| 10 | `styles.py` | `render_footer()` used a fragile `.replace('{date}', _today_ist())` pattern that worked but was obscure and would break if the date string ever contained `{` or `}` | Direct f-string interpolation: `Generated on {date_str}` |
| 11 | `retrieval.py` | `chromadb.PersistentClient` was created at module-import time, holding a stale SQLite connection if the DB folder was deleted between runs | Lazy `_get_collection()` — creates client on first use |
| 12 | `pdf_export.py` | ReportLab `Canvas.wedge()` doesn't accept keyword args (`startAngle=`, `extent=`) | Pass them positionally: `c.wedge(x1, y1, x2, y2, 90, -(score*3.6), fill=1, stroke=0)` |

## How to run

```bash
pip install -r requirements.txt
export GROQ_API_KEY="your-key-here"
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

**First run:** ChromaDB will download the `all-MiniLM-L6-v2` embedding model
(~80 MB, one-time) and auto-load the 12-section corpus from `data/corpus.json`.
Subsequent runs reuse the cached model and persistent DB.

## Design system

| Token | Value | Used for |
|-------|-------|----------|
| `PAPER` | `#F7F5F0` | ivory page background |
| `INK` | `#1A1A1A` | body text |
| `NAVY` | `#1B2A4A` | headings, primary button, accent text |
| `SEAL_RED` | `#8C1D1D` | "gap" status, seal stamps, critical severity |
| `GOLD` | `#B08D57` | emblem rim, "unclear" status, minor severity, accent rules |
| `COMPLIANT_GREEN` | `#4C6B3F` | "compliant" status, grade A |
| `MAJOR_ORANGE` | `#C97A1D` | major severity (between red and gold) |

**Typography:**
- Display: Source Serif 4 (with Lora fallback) — headings, masthead, seal text
- Body: IBM Plex Sans — UI text, descriptions
- Mono: IBM Plex Mono — citations, reference numbers, status pills

**Custom components** (rendered via `components.v1.html()`):
- `render_hero()` — letterhead masthead with file-reference number, CSS-drawn
  emblem (layered radial gradient + gold rim + dashed inner ring), and tagline
- `render_notice_header(findings, score, grade, grade_color, score_summary)` —
  "NOTICE OF FINDINGS" masthead with a CSS conic-gradient score gauge, live
  tally of total / gaps / unclear / compliant / critical / major, and the
  one-line score summary
- `render_finding_cards(sources, findings)` — per-finding cards with status
  pills, severity badges, penalty exposure rows, and CSS-drawn seal stamps
  bearing the act abbreviation. Staggered scroll-triggered reveal via
  IntersectionObserver. Iframe height computed up-front by
  `estimate_cards_height(sources, findings)` based on actual text length
  per card + penalty rows
- `render_footer()` — "Issued by ComplianceMind" signature block with
  IST date (uses `Asia/Kolkata` timezone, not UTC)

**PDF export** (`pdf_export.py`):
- `generate_certificate(business_desc, findings, sources, score, grade, ...)` →
  PDF bytes. Uses ReportLab with built-in fonts (Times, Helvetica, Courier)
  so it renders identically on any system. Currency written as "Rs." (not
  the rupee symbol) to avoid font-coverage issues. Score gauge drawn as a
  colored ring via `Canvas.wedge()`.
