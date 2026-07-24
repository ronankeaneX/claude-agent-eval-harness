"""Smoke test: one API call proving structured output works."""

import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

fake_ticket = (
    "Hi, I was charged twice for my subscription this month and the second "
    "charge overdrew my account. I need this fixed today please."
)

triage_tool = {
    "name": "record_triage",
    "description": "Record the triage classification for a support ticket.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["billing", "technical", "account", "other"],
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "needs_human": {"type": "boolean"},
        },
        "required": ["category", "urgency", "needs_human"],      
    },
}

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=500,
    tools=[triage_tool],
    tool_choice={"type": "tool", "name": "record_triage"},
    messages=[
        {"role": "user", "content": f"Triage this support ticket:\n\n{fake_ticket}"}
    ],
)

result = response.content[0].input

print("Category:   ", result["category"])
print("Urgency:    ", result["urgency"])
print("Needs human:", result["needs_human"])