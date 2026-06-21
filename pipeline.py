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
# Retrieval import — swap this single line for the real module when ready
# ---------------------------------------------------------------------------
from retrieval_stub import retrieve_sections  # TODO: swap for teammate's real retrieval.py


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

    Returns a list of dicts, each with: act, section, status, reasoning.
    status is one of: "compliant", "gap", "unclear".
    """
    model = "llama-3.3-70b-versatile"
    system_prompt = textwrap.dedent("""\
        You are an Indian legal compliance analyst.

        CRITICAL GROUNDING RULE — READ THIS CAREFULLY:
        You must ONLY reason over the statute sections provided below.
        Do NOT use any legal knowledge from your training data.
        Do NOT mention any law, section, or requirement that is not
        explicitly present in the provided sections.
        If a section is not provided, you have NO basis to comment on it.
        This constraint is essential to prevent hallucinated legal advice.

        Given:
        1. A set of extracted business facts (JSON)
        2. A list of retrieved Indian statute sections (JSON array)

        For EACH retrieved section, determine whether the described business
        is likely compliant, has a compliance gap, or the situation is unclear
        based SOLELY on the facts and the text of that section.

        Return ONLY a valid JSON array, no markdown, no other text:
        [
          {
            "act": "<full act name>",
            "section": "<section number>",
            "status": "<compliant | gap | unclear>",
            "reasoning": "<one sentence explaining your assessment, citing the specific section text>"
          }
        ]

        Rules:
        - Base your analysis ONLY on the provided section text.
        - If the facts don't provide enough information to judge compliance
          with a section, set status to "unclear".
        - Keep reasoning to one concise sentence.
    """)

    user_prompt = (
        f"Business facts:\n```json\n{json.dumps(facts, indent=2)}\n```\n\n"
        f"Retrieved statute sections:\n```json\n{json.dumps(retrieved_sections, indent=2)}\n```"
    )

    raw = _call_llm(model, system_prompt, user_prompt)
    return _parse_json_with_retry(raw, model, system_prompt, user_prompt)


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

    # Step 4: Score compliance
    findings = score_compliance(facts, sections)

    # Step 5: Generate recommendations report
    report = generate_recommendations(findings)

    return {
        "needs_clarification": False,
        "report": report,
        "findings": findings,
        "sources": sections,
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
