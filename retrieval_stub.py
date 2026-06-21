"""
Mock retrieval module — simulates teammate's ChromaDB-backed retrieval function.
Returns hardcoded statute sections based on keyword matching.
Swap this file for the real retrieval.py when the teammate's module is ready.
"""


# ---------------------------------------------------------------------------
# Hardcoded statute excerpts (placeholder text — will be replaced by real
# ChromaDB results once the retrieval half is integrated)
# ---------------------------------------------------------------------------

_DPDP_CONSENT = {
    "act": "Digital Personal Data Protection Act, 2023",
    "section": "Section 6",
    "title": "Consent",
    "text": (
        "Personal data may be processed by a Data Fiduciary only in accordance "
        "with the provisions of this Act and for a lawful purpose — (a) for which "
        "the Data Principal has given consent, or (b) for certain legitimate uses. "
        "Consent must be free, specific, informed, unconditional, and unambiguous, "
        "with a clear affirmative action signifying agreement."
    ),
}

_DPDP_NOTICE = {
    "act": "Digital Personal Data Protection Act, 2023",
    "section": "Section 5",
    "title": "Notice",
    "text": (
        "Every Data Fiduciary shall, before or at the time of collection of personal "
        "data, give to the Data Principal an itemised notice in clear and plain "
        "language containing a description of personal data being collected and the "
        "purpose of processing, along with the manner in which the Data Principal "
        "may exercise rights under this Act."
    ),
}

_IT_ACT_BREACH = {
    "act": "Information Technology Act, 2000",
    "section": "Section 43A",
    "title": "Compensation for failure to protect data",
    "text": (
        "Where a body corporate, possessing, dealing or handling any sensitive "
        "personal data or information in a computer resource which it owns, controls "
        "or operates, is negligent in implementing and maintaining reasonable security "
        "practices and procedures and thereby causes wrongful loss or wrongful gain "
        "to any person, such body corporate shall be liable to pay damages by way of "
        "compensation to the person so affected."
    ),
}

_IT_ACT_PAYMENT = {
    "act": "Information Technology Act, 2000",
    "section": "Section 72A",
    "title": "Punishment for disclosure of information in breach of lawful contract",
    "text": (
        "Any person including an intermediary who, while providing services under the "
        "terms of lawful contract, has secured access to any material containing "
        "personal information about another person, with the intent to cause or "
        "knowing that he is likely to cause wrongful loss or wrongful gain, discloses, "
        "without the consent of the person concerned, such material to any other "
        "person, shall be punished with imprisonment for a term which may extend to "
        "three years, or with fine up to five lakh rupees, or with both."
    ),
}

_CPA_UNFAIR_TRADE = {
    "act": "Consumer Protection Act, 2019",
    "section": "Section 2(47)",
    "title": "Unfair trade practice",
    "text": (
        "'Unfair trade practice' means a trade practice which, for the purpose of "
        "promoting the sale, use or supply of any goods or provision of any service, "
        "adopts any unfair method or unfair or deceptive practice including making "
        "any statement, whether orally or in writing or by visible representation "
        "which falsely represents that the goods are of a particular standard, "
        "quality, quantity, grade, composition, style or model."
    ),
}


def retrieve_sections(query: str, n_results: int = 3) -> list[dict]:
    """Return mock statute sections relevant to *query*.

    Performs simple keyword matching to simulate different retrieval results
    for different business descriptions.  Replace this entire module with the
    real ChromaDB-backed retrieval once it's ready.
    """
    q = query.lower()
    results: list[dict] = []

    # --- keyword-based routing -------------------------------------------
    if any(kw in q for kw in ("data", "personal", "user", "collect", "privacy")):
        results.append(_DPDP_CONSENT)
        results.append(_DPDP_NOTICE)

    if any(kw in q for kw in ("payment", "pay", "transaction", "fintech", "upi")):
        results.append(_IT_ACT_PAYMENT)

    if any(kw in q for kw in ("online", "website", "app", "internet", "digital", "saas")):
        results.append(_IT_ACT_BREACH)

    if any(kw in q for kw in ("sell", "product", "ecommerce", "e-commerce", "consumer", "customer")):
        results.append(_CPA_UNFAIR_TRADE)

    # Fallback: if nothing matched (very generic query), return the most
    # common entries so the pipeline still has something to reason over.
    if not results:
        results = [_DPDP_CONSENT, _IT_ACT_BREACH, _CPA_UNFAIR_TRADE]

    # Deduplicate (in case multiple keywords hit the same entry) and cap.
    seen, unique = set(), []
    for r in results:
        key = (r["act"], r["section"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:n_results]
