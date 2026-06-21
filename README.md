# ComplianceMind

**AI-Powered Legal Compliance for Indian SMEs**

A grounded, citation-first compliance assistant — built on Retrieval-Augmented Generation, not guesswork.

> The Arch: RAG & Agentic AI Hackathon · Legal Services Track

🔗 **Live Demo:** [hackathonraglaw-lztu5kmsrr5ayv7frbcefq.streamlit.app](https://hackathonraglaw-lztu5kmsrr5ayv7frbcefq.streamlit.app/)

---

## The Problem

- **Legal Blind Spots** — Indian SMEs don't know which laws govern their operations (data collection, e-commerce, payments, and more).
- **Hallucinated Advice** — Generic LLMs paraphrase legal guidance without grounding, which is dangerous in compliance contexts.
- **The Real Need** — A system that retrieves actual statute text, not vague summaries or confident guesses.

## Why ComplianceMind Is RAG — Not "Just ChatGPT"

Every legal claim ComplianceMind makes is grounded in retrieved, verifiable source text from Indian statute law. The system cites the exact **Act, Section, and Rule** — not a vague summary. Reviewers can always ask "Where did that come from?" and get an exact clause back.

| Generic LLM | ComplianceMind RAG |
|---|---|
| Paraphrased guesses | Retrieves actual statute text |
| No citations | Cites Act + Section + Rule |
| Hallucination risk | Verifiable sources |
| Unverifiable output | Defensible output |

## System Architecture

```
User Query → 4-Chain Orchestration → Final Report
```

A clean 4-chain orchestration ensures every stage's output feeds the next — from raw query to a fully cited compliance report.

### The 4-Chain Pipeline

`Intake → Retrieval → Scoring → Recommendation`

Each stage's structured output feeds the next, ensuring the final report is grounded, scored, and actionable.

**LLM provider:** Groq API (low-latency inference)

## Knowledge Base

12 statute sections sourced directly from primary government sources — `indiacode.nic.in` and official PDFs.

| Source | Coverage |
|---|---|
| DPDP Act 2023 | Sec 4, 5, 6, 8 |
| IT Act 2000 | Sec 43A, 72, 72A |
| Consumer Protection Act 2019 | Sec 2(47) |
| CP (E-Commerce) Rules 2020 | Rule 4 (3 sub-chunks) |
| GST Act | Sec 22 |

Vector store: **ChromaDB** (persistent, local) · Embedding model: **all-MiniLM-L6-v2**

## Demo

**Query:**
> "I run an e-commerce store and collect customer phone numbers. What laws apply to me?"

**Output:**
- DPDP Act 2023 — Sec 5 (notice & consent obligations)
- CP (E-Commerce) Rules 2020 — Rule 4(2) (grievance officer)
- IT Act 2000 — Sec 43A (data breach liability)

Every claim links to an exact Act + Section — fully auditable.

## Tech Stack

| Component | Role |
|---|---|
| **ChromaDB** | Persistent local vector store for statute embeddings (`all-MiniLM-L6-v2`) |
| **Groq API** | Ultra-low-latency LLM inference powering all 4 orchestration stages |
| **Streamlit** | Lightweight Python UI (`app.py`) for query input and report display |
| **Python** | Full backend (`pipeline.py`) orchestrating retrieval, scoring, and generation |

## Engineering Challenges & Fixes

1. **False positives from large chunks** — Multi-topic Rule 4 chunks matched unrelated queries → split into 3 focused sub-chunks, improving retrieval precision.
2. **Stale embeddings in ChromaDB** — "Ghost" embeddings persisted after corpus edits → rebuilt the vector store from scratch after structural changes.
3. **Sparse corpus & negative queries** — Offline business queries returned weak matches → pushed relevance judgment into the LLM reasoning layer rather than relying on retrieval alone.

## Why It Matters

ComplianceMind helps non-lawyers self-assess compliance risk in plain language — grounded in real statute law, making it defensible, auditable, and trustworthy.

## Known Limitations

The 12-section corpus means sparse edge-case coverage. This is mitigated by downstream LLM reasoning rather than blind trust in retrieval.

## Getting Started (Run Locally)

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd <your-repo-folder>

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Groq API key
echo "GROQ_API_KEY=your_key_here" > .env

# 5. Run the app
streamlit run app.py
```

The app will be live at:

```
http://localhost:8501
```

## Roadmap

- Expand corpus coverage
- Add re-ranking
- Surface confidence scores

---

*Built for The Arch: RAG & Agentic AI Hackathon — Legal Services Track.*
