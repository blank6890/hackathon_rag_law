"""
ComplianceMind — LLM reasoning pipeline.

Orchestrates: fact extraction → retrieval → compliance scoring → recommendations.
All LLM calls go through the Groq SDK (reads GROQ_API_KEY from env).

BUGFIXES vs original:
  1. Lazy Groq client init — original did `_client = Groq()` at module
     import time, which crashes the whole app if GROQ_API_KEY is unset,
     even before the user clicks anything. Now the client is created
     on first use inside _call_llm().
  2. Empty retrieval guard — if retrieve_sections() returns [], the
     scoring LLM gets nothing useful and may hallucinate. Now we short-
     circuit with a friendly "no applicable statutes" message.
  3. Clarification logic — original checked
     `facts.get("collects_personal_data") is None` but the LLM is asked
     to return a bool, so the check never triggered. We now rely
     solely on the `is_vague` flag (which is what the prompt actually
     controls), and generate a more useful clarifying question by
     inspecting which fields the LLM left blank/empty-string.
"""

import json
import os
import textwrap
from typing import Any

from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file if it exists
load_dotenv()


# ---------------------------------------------------------------------------
# Retrieval import — uses the real ChromaDB-backed retrieval module.
# The retrieval module auto-loads the corpus on first use, so no manual
# setup is needed. Falls back to the keyword stub if chromadb is not
# installed (e.g. in a stripped-down test environment).
# ---------------------------------------------------------------------------
try:
    from retrieval import retrieve_sections  # real ChromaDB-backed retrieval
except Exception:
    # Fallback: use the keyword stub (e.g. if chromadb isn't installed)
    from retrieval_stub import retrieve_sections


# ---------------------------------------------------------------------------
# Groq client (lazy singleton — created on first use, not at import time)
# ---------------------------------------------------------------------------
_client: Groq | None = None


def _get_client() -> Groq:
    """Return a singleton Groq client, instantiating it on first use.

    Reading GROQ_API_KEY happens here, not at module load — so importing
    pipeline.py (e.g. for unit tests, or just to render the UI shell)
    never crashes the app for missing credentials. The error surfaces
    only when the user actually triggers an LLM call.
    """
    global _client
    if _client is None:
        _client = Groq()  # reads GROQ_API_KEY from environment
    return _client


# ========================== HELPER ========================================
def _call_llm(model: str, system_prompt: str, user_prompt: str,
              temperature: float = 0) -> str:
    """Send a chat-completion request and return the assistant's text."""
    response = _get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _strip_code_fence(raw: str) -> str:
    """Strip ```...``` markdown fences if the model wrapped its output."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]  # remove opening fence line
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    return cleaned


def _parse_json_with_retry(raw: str, model: str, system_prompt: str,
                           user_prompt: str, temperature: float = 0) -> Any:
    """Try to parse *raw* as JSON; on failure retry the LLM once with a
    stricter prompt, then raise a clear error."""
    # First attempt — try parsing what we got
    try:
        return json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError:
        pass

    # Retry with a much stricter prompt
    strict_system = (
        system_prompt
        + "\n\nCRITICAL: Your previous response was not valid JSON. "
        "This time you MUST return ONLY a raw JSON object/array. "
        "No markdown, no code fences, no explanation — just JSON."
    )
    raw2 = _call_llm(model, strict_system, user_prompt, temperature)
    try:
        return json.loads(_strip_code_fence(raw2))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON even after retry.\n"
            f"Last raw output:\n{raw2}"
        ) from exc


# ========================== PIPELINE STEPS ================================

def extract_facts(user_input: str) -> dict:
    """Use llama-3.1-8b-instant to extract structured business facts.

    Returns dict with keys: industry, collects_personal_data (bool),
    data_types (list), is_online (bool), processes_payments (bool),
    is_vague (bool).
    """
    model = "llama-3.1-8b-instant"
    system_prompt = textwrap.dedent("""\
        You are a business-fact extraction assistant.
        Given a user's plain-English description of their business, extract
        the following fields and return ONLY valid JSON, no markdown formatting,
        no other text:

        {
          "industry": "<string — best-guess industry, e.g. 'fintech', 'edtech', 'ecommerce'>",
          "collects_personal_data": <true/false>,
          "data_types": ["<list of data types collected, e.g. 'name', 'email', 'payment info'>"],
          "is_online": <true/false — whether the business operates online>,
          "processes_payments": <true/false>,
          "is_vague": <true/false — set to true ONLY if the input is too unclear
                       or too short to confidently extract the above fields>
        }

        Rules:
        - If a field cannot be determined, make a reasonable assumption and
          set is_vague to false, UNLESS the input is genuinely too vague
          (e.g. just "I'm building an app" with no further detail).
        - Return ONLY the JSON object.  No explanation, no markdown.
    """)
    raw = _call_llm(model, system_prompt, user_input)
    return _parse_json_with_retry(raw, model, system_prompt, user_input)


def score_compliance(facts: dict, retrieved_sections: list[dict]) -> list[dict]:
    """Use llama-3.3-70b-versatile to assess compliance against retrieved sections.

    Returns a list of dicts, each with: act, section, status, severity,
    penalty_range, citation_trust, role, enforcement_trigger, reasoning.

    status is one of: "compliant", "gap", "unclear".
    severity is one of: "critical", "major", "minor".
    penalty_range is a short string citing the penalty from the section text.
    citation_trust is "direct" (section text directly addresses the business
      situation) or "inferred" (LLM reasoned by analogy from the section).
    role is who in the org should care: "Founder", "Legal", "Engineering",
      "DPO", or "Finance".
    enforcement_trigger is a short string describing WHEN this rule applies
      (e.g. "Immediate", "At Rs. 20L turnover", "When you store any personal data").
    """
    model = "llama-3.3-70b-versatile"
    system_prompt = textwrap.dedent("""\
        You are an Indian legal compliance analyst.

        CRITICAL GROUNDING RULE — READ THIS CAREFULLY:
        You must ONLY reason over the statute sections provided below.
        Do NOT use any legal knowledge from your training data.
        Do NOT mention any law, section, or requirement that is not
        explicitly present in the provided sections.

        Given:
        1. A set of extracted business facts (JSON)
        2. A list of retrieved Indian statute sections (JSON array)

        For EACH retrieved section, determine whether the described business
        is likely compliant, has a compliance gap, or the situation is unclear.

        Additionally, for each finding:
        - severity: rate the RISK (critical/major/minor) based on worst-case
          penalty mentioned in the section.
        - penalty_range: extract the SPECIFIC penalty from the section text.
          If none mentioned, set to "Not specified in section".
        - citation_trust: "direct" if the section text DIRECTLY addresses the
          business's situation (e.g. the business collects personal data and
          the section is about personal data collection), or "inferred" if you
          had to reason by analogy (e.g. the section is about banks but the
          business is a fintech startup).
        - role: who in the org should care about this finding — one of:
          "Founder" (strategic decisions), "Legal" (legal review needed),
          "Engineering" (technical implementation), "DPO" (Data Protection
          Officer / privacy), "Finance" (tax/payments/registration).
        - enforcement_trigger: a SHORT phrase (under 40 chars) describing WHEN
          this rule applies to the business. Examples:
          "Immediate" (applies as soon as you operate)
          "At Rs. 20L turnover" (GST registration threshold)
          "When you store personal data" (IT Act 43A)
          "On first user transaction" (payment rules)

        Return ONLY a valid JSON array, no markdown, no other text:
        [
          {
            "act": "<full act name>",
            "section": "<section number>",
            "status": "<compliant | gap | unclear>",
            "severity": "<critical | major | minor>",
            "penalty_range": "<short penalty string>",
            "citation_trust": "<direct | inferred>",
            "role": "<Founder | Legal | Engineering | DPO | Finance>",
            "enforcement_trigger": "<short phrase under 40 chars>",
            "reasoning": "<one sentence citing the section text>"
          }
        ]
    """)

    user_prompt = (
        f"Business facts:\n```json\n{json.dumps(facts, indent=2)}\n```\n\n"
        f"Retrieved statute sections:\n```json\n{json.dumps(retrieved_sections, indent=2)}\n```"
    )

    raw = _call_llm(model, system_prompt, user_prompt)
    findings = _parse_json_with_retry(raw, model, system_prompt, user_prompt)

    # Backfill all new fields for any findings where the LLM omitted them.
    for f in findings:
        f.setdefault("severity", "minor")
        f.setdefault("penalty_range", "Not specified in section")
        f.setdefault("citation_trust", "inferred")
        f.setdefault("role", "Founder")
        f.setdefault("enforcement_trigger", "Immediate")

    return findings


# ========================== COMPLIANCE SCORE ===============================
# Severity weights — how many points each finding type costs.
# Tuned so that:
#   - A perfectly compliant business scores 100 (A grade)
#   - One critical gap drops you to 75 (B grade)
#   - Two critical gaps drop you to 50 (D grade)
#   - Three+ critical gaps drop you to F
_SEVERITY_WEIGHTS = {
    "critical": 25,
    "major": 12,
    "minor": 5,
}

# Unclear items cost a flat 3 points regardless of severity — they're
# not gaps, but they represent unresolved risk.
_UNCLEAR_PENALTY = 3


def compute_compliance_score(findings: list[dict]) -> dict:
    """Compute a 0-100 compliance score and letter grade from findings.

    Formula:
        score = 100
              - (sum of severity_weight[gap.severity] for each gap)
              - (UNCLEAR_PENALTY * count of unclear items)

    Grade:
        A: 90-100  (excellent)
        B: 75-89   (good, minor gaps)
        C: 60-74   (moderate risk)
        D: 45-59   (significant risk)
        F: 0-44    (critical risk)

    Returns dict with: score (int 0-100), grade (str), grade_color (hex),
      summary (str, one-line human-readable).
    """
    score = 100
    gap_count = 0
    unclear_count = 0
    compliant_count = 0
    critical_gaps = 0
    major_gaps = 0
    minor_gaps = 0

    for f in findings:
        status = (f.get("status") or "").lower()
        severity = (f.get("severity") or "minor").lower()

        if status == "gap":
            gap_count += 1
            weight = _SEVERITY_WEIGHTS.get(severity, 5)
            score -= weight
            if severity == "critical":
                critical_gaps += 1
            elif severity == "major":
                major_gaps += 1
            else:
                minor_gaps += 1
        elif status == "unclear":
            unclear_count += 1
            score -= _UNCLEAR_PENALTY
        elif status == "compliant":
            compliant_count += 1

    score = max(0, min(100, score))

    if score >= 90:
        grade, grade_color = "A", "#4C6B3F"  # compliant green
    elif score >= 75:
        grade, grade_color = "B", "#B08D57"  # gold
    elif score >= 60:
        grade, grade_color = "C", "#B08D57"  # gold
    elif score >= 45:
        grade, grade_color = "D", "#8C1D1D"  # seal red
    else:
        grade, grade_color = "F", "#8C1D1D"  # seal red

    # One-line summary
    parts = []
    if critical_gaps:
        parts.append(f"{critical_gaps} critical gap{'s' if critical_gaps != 1 else ''}")
    if major_gaps:
        parts.append(f"{major_gaps} major gap{'s' if major_gaps != 1 else ''}")
    if minor_gaps:
        parts.append(f"{minor_gaps} minor gap{'s' if minor_gaps != 1 else ''}")
    if unclear_count:
        parts.append(f"{unclear_count} unclear")
    if compliant_count:
        parts.append(f"{compliant_count} compliant")

    if not parts:
        summary = "No findings to report."
    elif gap_count == 0 and unclear_count == 0:
        summary = f"Fully compliant across {compliant_count} section{'s' if compliant_count != 1 else ''} reviewed."
    else:
        summary = f"Score {score}/100 (grade {grade}): " + ", ".join(parts) + f", {compliant_count} compliant."

    return {
        "score": score,
        "grade": grade,
        "grade_color": grade_color,
        "summary": summary,
        "breakdown": {
            "critical_gaps": critical_gaps,
            "major_gaps": major_gaps,
            "minor_gaps": minor_gaps,
            "unclear": unclear_count,
            "compliant": compliant_count,
            "total": len(findings),
        },
    }


def generate_recommendations(findings: list[dict]) -> str:
    """Use llama-3.1-8b-instant to generate a plain-English markdown report.

    Returns a markdown string with a one-line risk summary and bulleted
    action items, each citing act + section.
    """
    model = "llama-3.1-8b-instant"
    system_prompt = textwrap.dedent("""\
        You are a friendly compliance advisor writing for a non-lawyer startup founder.

        Given a JSON array of compliance findings (each with act, section,
        status, and reasoning), produce a concise markdown report:

        1. Start with a one-line **Risk Summary** (e.g. "⚠️ 2 gaps found across 3 laws reviewed").
        2. Then a bulleted **Action Items** list.  For each gap or unclear item:
           - State what the founder should do in plain language (no legal jargon).
           - Cite the act and section in parentheses at the end of each bullet.
        3. If everything is compliant, say so positively and still list what
           was checked with citations.

        Do NOT invent any findings not in the input.  Use only what is provided.
        Return ONLY the markdown report.
    """)
    user_prompt = json.dumps(findings, indent=2)
    return _call_llm(model, system_prompt, user_prompt, temperature=0.3)


# ========================== FOLLOW-UP CHAT ================================

def answer_followup(question: str, findings: list[dict],
                    sources: list[dict], business_desc: str) -> str:
    """Answer a follow-up question in the context of the compliance report.

    Uses llama-3.3-70b-versatile so the answer is grounded in the same
    statute sections that produced the findings. The LLM is explicitly
    told to only use the provided findings/sources and not hallucinate.
    """
    model = "llama-3.3-70b-versatile"
    system_prompt = textwrap.dedent("""\
        You are a friendly compliance advisor. The user has already run a
        compliance check on their business and is now asking a follow-up
        question. Answer based ONLY on the findings and statute sections
        provided below. If the question is about something not covered in
        the findings, say so honestly and suggest they re-run the check
        with an updated business description.

        Keep the answer concise (2-4 sentences). Use plain language.
        Cite the act and section in parentheses where relevant.
    """)
    user_prompt = (
        f"Business description:\n{business_desc}\n\n"
        f"Findings:\n```json\n{json.dumps(findings, indent=2)}\n```\n\n"
        f"Statute sections:\n```json\n{json.dumps(sources, indent=2)}\n```\n\n"
        f"Follow-up question:\n{question}"
    )
    return _call_llm(model, system_prompt, user_prompt, temperature=0.3)


# ========================== TRANSLATION ===================================

_SUPPORTED_LANGUAGES = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "தமிழ் (Tamil)": "ta",
    "বাংলা (Bengali)": "bn",
}


def get_supported_languages() -> dict:
    """Return the dict of supported languages (label -> code)."""
    return dict(_SUPPORTED_LANGUAGES)


def translate_report(report: str, target_language: str) -> str:
    """Translate the markdown report into the target language.

    target_language is a language code like 'hi', 'ta', 'bn'.
    'en' returns the report unchanged.
    """
    if target_language == "en" or not target_language:
        return report

    lang_name = {
        "hi": "Hindi", "ta": "Tamil", "bn": "Bengali",
    }.get(target_language, target_language)

    model = "llama-3.3-70b-versatile"
    system_prompt = textwrap.dedent(f"""\
        You are a legal translator. Translate the following compliance report
        into {lang_name}. Keep all markdown formatting intact. Keep the act
        names and section numbers in English (they are proper nouns), but
        translate the surrounding text. Keep citations like
        "(DPDP Act 2023, Section 5)" unchanged.

        Return ONLY the translated markdown. No preamble.
    """)
    return _call_llm(model, system_prompt, report, temperature=0.2)


# ========================== ORCHESTRATOR ==================================

def run_pipeline(user_input: str) -> dict:
    """Full pipeline: extract → retrieve → score → recommend.

    Returns:
        If input is too vague:
            {"needs_clarification": True, "message": "<clarifying question>"}
        If no relevant statutes were retrieved:
            {"needs_clarification": True, "message": "<no-applicable-statutes msg>"}
        Otherwise:
            {"needs_clarification": False, "report": "<markdown>",
             "findings": [<list>], "sources": [<list>]}
    """
    # Step 1: Extract business facts
    facts = extract_facts(user_input)

    # Step 2: Check if input is too vague
    if facts.get("is_vague", False):
        # Build a clarifying question based on which fields are empty or
        # clearly defaulted. NOTE: the LLM returns booleans for the
        # yes/no fields, so we can't use `is None` — we look at the
        # string fields and data_types list instead, which is where
        # vagueness actually shows up.
        missing_parts = []
        if not facts.get("industry"):
            missing_parts.append("what industry you're in")
        if not facts.get("data_types"):
            missing_parts.append("what kind of data you collect from users")
        if not facts.get("is_online") and not facts.get("processes_payments"):
            missing_parts.append("whether you operate online or process payments")

        if missing_parts:
            message = (
                "Your description is a bit too brief for a thorough analysis. "
                f"Could you clarify: {', '.join(missing_parts)}? "
                "The more specific you are, the more accurate the citations will be."
            )
        else:
            message = (
                "Your description is a bit too brief for a thorough analysis. "
                "Could you tell me more about what your business does, what "
                "data you collect, and whether you operate online or process payments?"
            )
        return {"needs_clarification": True, "message": message}

    # Step 3: Retrieve relevant statute sections
    sections = retrieve_sections(user_input)

    # BUGFIX: guard against empty retrieval — scoring an empty section list
    # would push the LLM to hallucinate. Better to surface a clear message.
    if not sections:
        return {
            "needs_clarification": True,
            "message": (
                "I couldn't find any Indian statute sections directly relevant "
                "to your description. Could you add a bit more detail about your "
                "business model — for example, whether you collect personal data, "
                "process payments, sell to consumers, or operate online?"
            ),
        }

    # Step 4: Score compliance (now includes severity + penalty per finding)
    findings = score_compliance(facts, sections)

    # Step 5: Generate recommendations report
    report = generate_recommendations(findings)

    # Step 6: Compute aggregate compliance score (0-100) + letter grade
    score_result = compute_compliance_score(findings)

    return {
        "needs_clarification": False,
        "report": report,
        "findings": findings,
        "sources": sections,
        "score": score_result["score"],
        "grade": score_result["grade"],
        "grade_color": score_result["grade_color"],
        "score_summary": score_result["summary"],
        "score_breakdown": score_result["breakdown"],
    }


# ========================== TEST HARNESS ==================================

if __name__ == "__main__":
    test_cases = [
        # Test 1: Clear case — an online ed-tech platform
        (
            "Clear case (edtech)",
            "We run an online education platform that collects student names, "
            "emails, and learning progress data. We sell courses directly to "
            "consumers through our website."
        ),
        # Test 2: Multi-law case — payments + personal data
        (
            "Multi-law case (fintech + data)",
            "We are building a fintech app that lets users make UPI payments. "
            "We collect personal data including names, phone numbers, Aadhaar "
            "numbers, and transaction history. We also sell financial products "
            "to consumers online."
        ),
        # Test 3: Deliberately vague
        (
            "Vague case",
            "I'm building an app."
        ),
    ]

    for label, description in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST: {label}")
        print(f"INPUT: {description}")
        print(f"{'='*70}")
        try:
            result = run_pipeline(description)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"ERROR: {e}")
