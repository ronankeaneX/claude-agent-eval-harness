"""Drift tripwire: the JSON enums in TOOL_DEFINITIONS must match the
Pydantic Literals in schemas.py. If someone updates one and forgets
the other, these tests fail loudly instead of letting the mismatch
cause silent bugs in production.
Design decision logged in CLAUDE.md: duplication accepted, protected by this test.
"""

from typing import get_args

from src.triage.agent import TOOL_DEFINITIONS
from src.triage.schemas import TriageResult


def _record_triage_schema() -> dict:
    """Find the record_triage tool definition and return its input_schema."""
    for tool in TOOL_DEFINITIONS:
        if tool["name"] == "record_triage":
            return tool["input_schema"]
    raise AssertionError("record_triage tool definition not found")


def test_category_enum_matches_literal():
    json_enum = _record_triage_schema()["properties"]["category"]["enum"]
    literal_values = get_args(TriageResult.model_fields["category"].annotation)
    assert set(json_enum) == set(literal_values)


def test_urgency_enum_matches_literal():
    json_enum = _record_triage_schema()["properties"]["urgency"]["enum"]
    literal_values = get_args(TriageResult.model_fields["urgency"].annotation)
    assert set(json_enum) == set(literal_values)