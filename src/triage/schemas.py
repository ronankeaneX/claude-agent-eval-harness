"""Data shapes for tickets and triage results."""

from pydantic import BaseModel
from typing import Literal

class Ticket(BaseModel):
    ticket_id: str
    customer_id: str
    text: str

class TriageResult(BaseModel):
    category: Literal["billing", "technical", "account", "other"]
    urgency: Literal[ "low", "medium", "high"]
    needs_human: bool
    reasoning: str