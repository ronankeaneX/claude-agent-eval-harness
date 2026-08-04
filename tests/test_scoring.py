"""Deterministic tests for the scoring and voting rules.

These cover the pure functions only: no API calls, no dataset reads, no cost.
The rules they pin down are the ones CLAUDE.md argues for at length, which
until now were defended only by paid sweeps and by check_voting.py, a
throwaway that no longer exists.

Rules under test:
  - _matches: list-valued expectations on explicitly ambiguous cases
  - score_case: FN and FP never blended; a None result is a FAILED run and
    counts as a false negative when a human was expected
  - _majority: strictly more than half, so an even tie FAILS
  - _aggregate: majority verdict for the headline, any-run flags for the
    intermittent misses a vote would otherwise absorb
  - flip detection: None is DISTINCT from False, never folded into it

One test documents a KNOWN LIMITATION rather than a desired property; it is
named and commented as such.
"""

from evals.scoring import _matches, score_case
from evals.run_evals import _aggregate, _fmt, _majority, _tally, _wrong
from src.triage.schemas import TriageResult


def _case(category="billing", urgency="medium", needs_human=False):
    """A minimal case dict with only the fields the scorer reads."""
    return {
        "case_id": "t_001",
        "case_type": "easy",
        "expected_category": category,
        "expected_urgency": urgency,
        "expected_needs_human": needs_human,
    }


def _result(category="billing", urgency="medium", needs_human=False,
            reasoning="routine request, nothing unusual"):
    return TriageResult(
        category=category,
        urgency=urgency,
        needs_human=needs_human,
        reasoning=reasoning,
    )


def _values(category=None, urgency=None, needs_human=None, trigger_cited=None):
    """The per-run value lists _aggregate reads for flip detection."""
    return {
        "category": category or ["billing"],
        "urgency": urgency or ["medium"],
        "needs_human": needs_human or [False],
        "trigger_cited": trigger_cited or [True],
    }


# --- _matches: scalar and list-valued expectations -------------------------

def test_matches_scalar_expectation():
    assert _matches("billing", "billing")
    assert not _matches("billing", "technical")


def test_matches_accepts_any_value_in_a_list():
    """Ambiguous cases carry acceptable-value SETS, fixed at authoring time."""
    assert _matches(["account", "billing"], "billing")
    assert _matches(["account", "billing"], "account")
    assert not _matches(["account", "billing"], "technical")


def test_matches_rejects_none():
    """A no-decision never matches, whatever the expectation."""
    assert not _matches("billing", None)
    assert not _matches(["account", "billing"], None)


# --- score_case: the two escalation failure directions ---------------------

def test_missed_escalation_is_a_false_negative_only():
    """Expected a human, did not get one. SAFETY signal."""
    scored = score_case(_case(needs_human=True), _result(needs_human=False))
    assert scored["false_negative"] is True
    assert scored["false_positive"] is False
    assert scored["escalation_pass"] is False


def test_over_escalation_is_a_false_positive_only():
    """A human looked at something they did not need to. COST signal."""
    scored = score_case(
        _case(needs_human=False),
        _result(needs_human=True, reasoning="possible security concern"),
    )
    assert scored["false_positive"] is True
    assert scored["false_negative"] is False
    assert scored["escalation_pass"] is False


def test_correct_escalation_is_neither():
    scored = score_case(
        _case(needs_human=True),
        _result(needs_human=True, reasoning="customer was charged twice"),
    )
    assert scored["false_negative"] is False
    assert scored["false_positive"] is False
    assert scored["escalation_pass"] is True


# --- score_case: a None result is a failed run, not a quiet pass -----------

def test_none_result_fails_every_field():
    scored = score_case(_case(), None)
    assert scored["deterministic_pass"] is False
    assert scored["category_pass"] is False
    assert scored["urgency_pass"] is False
    assert scored["escalation_pass"] is False
    assert scored["note"] == "agent returned no decision"


def test_none_result_counts_as_a_missed_escalation_when_a_human_was_expected():
    """Never deciding is a loop or safety-stop defect, but the customer still
    did not get a human. It belongs in the FN column."""
    scored = score_case(_case(needs_human=True), None)
    assert scored["false_negative"] is True
    assert scored["false_positive"] is False


def test_none_result_is_not_a_false_positive_when_no_human_was_expected():
    scored = score_case(_case(needs_human=False), None)
    assert scored["false_negative"] is False
    assert scored["false_positive"] is False


# --- score_case: list-valued expectations reach the verdict ----------------

def test_ambiguous_case_passes_on_either_acceptable_value():
    case = _case(category=["account", "billing"], urgency=["medium", "high"])
    for category in ("account", "billing"):
        for urgency in ("medium", "high"):
            scored = score_case(case, _result(category=category, urgency=urgency))
            assert scored["deterministic_pass"] is True, (category, urgency)


# --- score_case: trigger citation gates the verdict -----------------------

def test_trigger_citation_is_not_required_when_the_agent_does_not_escalate():
    scored = score_case(_case(needs_human=False), _result(needs_human=False))
    assert scored["trigger_cited"] is True


def test_escalating_without_naming_a_trigger_fails_the_verdict():
    """trigger_cited is the fourth condition in deterministic_pass, so an
    otherwise-correct escalation still fails if it names nothing."""
    scored = score_case(
        _case(needs_human=True),
        _result(needs_human=True, reasoning="this one looks important"),
    )
    assert scored["trigger_cited"] is False
    assert scored["escalation_pass"] is True
    assert scored["category_pass"] is True
    assert scored["urgency_pass"] is True
    assert scored["deterministic_pass"] is False


def test_trigger_citation_is_substring_only_KNOWN_LIMITATION():
    """DOCUMENTS CURRENT BEHAVIOR, NOT DESIRED BEHAVIOR.

    The check is a blunt substring match over TRIGGER_KEYWORDS, so reasoning
    that NEGATES a trigger is credited for citing it. See the trigger_cited
    entry in CLAUDE.md open threads. Tightening this is an INSTRUMENT change:
    it voids the 8/17 baseline and requires a re-sweep, so the defect is
    pinned here rather than silently fixed. If this test starts failing,
    someone tightened the check on purpose - update it and re-baseline.
    """
    scored = score_case(
        _case(needs_human=True),
        _result(needs_human=True, reasoning="No prior ticket history and no security concern."),
    )
    assert scored["trigger_cited"] is True


# --- _majority: strictly more than half ------------------------------------

def test_majority_needs_strictly_more_than_half():
    assert _majority([True, True, False]) is True
    assert _majority([True, False, False]) is False
    assert _majority([True, True, True]) is True
    assert _majority([False, False, False]) is False


def test_even_tie_fails():
    """No majority means no verdict to gate on."""
    assert _majority([True, False]) is False
    assert _majority([True, True, False, False]) is False


# --- _aggregate: majority verdict vs any-run diagnostics -------------------

def test_intermittent_missed_escalation_survives_the_vote():
    """A case that fails to escalate on even 1 of n runs is a probabilistic
    miss in production. The majority absorbs it; any_false_negative must not."""
    runs = [
        score_case(_case(needs_human=True), _result(needs_human=False)),
        score_case(_case(needs_human=True),
                   _result(needs_human=True, reasoning="customer was charged twice")),
        score_case(_case(needs_human=True),
                   _result(needs_human=True, reasoning="customer was charged twice")),
    ]
    row = _aggregate(_case(needs_human=True), runs,
                     _values(needs_human=[False, True, True]))
    assert row["false_negative"] is False       # absorbed by the majority
    assert row["any_false_negative"] is True    # still reported


def test_aggregate_counts_no_decision_runs():
    runs = [score_case(_case(), None), score_case(_case(), _result())]
    row = _aggregate(_case(), runs, _values())
    assert row["none_count"] == 1


# --- flip detection: None is distinct from False --------------------------

def test_a_field_that_settles_on_one_value_did_not_flip():
    row = _aggregate(_case(), [score_case(_case(), _result())],
                     _values(urgency=["medium", "medium", "medium"]))
    assert "urgency" not in row["flipped"]


def test_disagreement_across_runs_is_a_flip():
    row = _aggregate(_case(), [score_case(_case(), _result())],
                     _values(urgency=["medium", "high", "medium"]))
    assert "urgency" in row["flipped"]


def test_none_is_not_folded_into_false():
    """'Never decided' is a loop defect; 'decided no' is a judgment defect.
    Treating them as the same value would hide one behind the other."""
    row = _aggregate(_case(), [score_case(_case(), _result())],
                     _values(needs_human=[None, False, False]))
    assert "needs_human" in row["flipped"]


# --- readout helpers -------------------------------------------------------

def test_no_decision_never_prints_as_none():
    """Printing None would read as if the agent chose null."""
    assert _fmt(None) == "NO-DECISION"
    assert _fmt(False) == "False"
    assert _fmt("high") == "high"


def test_tally_keeps_first_seen_order_with_counts():
    assert _tally(["high", "medium", "high"]) == "high x2, medium x1"
    assert _tally([None, "low"]) == "NO-DECISION x1, low x1"


# --- _wrong: the readout must agree with the scorer -----------------------

def test_wrong_uses_plain_equality_for_needs_human():
    assert _wrong("needs_human", True, [True, True]) is False
    assert _wrong("needs_human", True, [True, False]) is True


def test_wrong_uses_matches_for_list_valued_expectations():
    """A field the gate counted as a pass must never display as wrong."""
    assert _wrong("category", ["account", "billing"], ["billing", "account"]) is False
    assert _wrong("category", ["account", "billing"], ["technical"]) is True


def test_a_no_decision_run_always_counts_as_a_miss():
    assert _wrong("urgency", "medium", [None]) is True
    assert _wrong("needs_human", True, [None]) is True
