"""Deterministic scoring: free, instant, never wrong. Runs on every case.

Design decisions embedded here:
- Ambiguous cases may carry a LIST of acceptable values (M2 decision).
  Sets were fixed at authoring time and are never widened to make a run pass.
- needs_human is scored strictly, and failures are split into false
  negatives (missed escalation, harms customers) and false positives
  (wasted human time). Never blended into one number.
- Trigger citation is checked HERE, not by the judge (M3 decision): the
  five triggers are known strings, so this needs no model call.
"""

TRIGGER_KEYWORDS = [
    "money", "charged", "overcharge", "refund", "fee", "overdraw", "overdrew",
    "legal", "lawyer", "dispute", "attorney",
    "security", "compromise", "unauthorized", "breach", "injection", "login from",
    "repeat", "prior ticket", "third time", "history",
    "seat", "upgrade", "renewal", "expansion", "revenue",
]


def _matches(expected, actual) -> bool:
    """Pass if actual equals expected, or is IN expected when expected is a list."""
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def score_case(case: dict, result) -> dict:
    """Score one case. `result` is a TriageResult, or None if the agent failed."""
    if result is None:
        return {
            "case_id": case["case_id"],
            "case_type": case["case_type"],
            "category_pass": False,
            "urgency_pass": False,
            "escalation_pass": False,
            "false_negative": case["expected_needs_human"] is True,
            "false_positive": False,
            "trigger_cited": False,
            "deterministic_pass": False,
            "note": "agent returned no decision",
        }

    category_pass = _matches(case["expected_category"], result.category)
    urgency_pass = _matches(case["expected_urgency"], result.urgency)
    escalation_pass = result.needs_human == case["expected_needs_human"]

    # The two escalation failure modes, kept separate on purpose.
    false_negative = case["expected_needs_human"] is True and result.needs_human is False
    false_positive = case["expected_needs_human"] is False and result.needs_human is True

    # Promoted from the judge: if it escalated, did it cite something real?
    lowered = result.reasoning.lower()
    if result.needs_human:
        trigger_cited = any(word in lowered for word in TRIGGER_KEYWORDS)
    else:
        trigger_cited = True  # not applicable when no escalation was claimed

    return {
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "category_pass": category_pass,
        "urgency_pass": urgency_pass,
        "escalation_pass": escalation_pass,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "trigger_cited": trigger_cited,
        "deterministic_pass": all(
            [category_pass, urgency_pass, escalation_pass, trigger_cited]
        ),
        "note": "",
    }