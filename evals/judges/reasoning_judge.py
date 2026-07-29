"""LLM-as-judge for the agent's reasoning field.

Advisory only: judge scores are reported but never gate a build (design
decision M3, Option A). Judges are models, so they are noisy; a gate that
fails builds for noisy reasons stops being trusted.

Rubric design rules applied here:
- explicit criteria, not "is this good?"
- structured output forced via tool use, so verdicts are data not prose
- one focused call per case, not five dimensions bundled together
"""

import anthropic

JUDGE_MODEL = "claude-sonnet-4-6"

JUDGE_TOOL = {
    "name": "record_judgment",
    "description": "Record the rubric scores for a piece of triage reasoning.",
    "input_schema": {
        "type": "object",
        "properties": {
            "identifies_issue": {
                "type": "boolean",
                "description": "Does the reasoning correctly identify what the ticket is actually about?",
            },
            "justifies_escalation": {
                "type": "boolean",
                "description": "If it escalated, does it name a legitimate trigger? If it did not escalate, does it explain why no trigger applies? True if the escalation stance is justified either way.",
            },
            "no_invented_facts": {
                "type": "boolean",
                "description": "Does the reasoning avoid asserting facts that the tools did not return?",
            },
            "score": {
                "type": "integer",
                "description": "Overall reasoning quality, 1 (poor) to 5 (excellent).",
            },
            "comment": {
                "type": "string",
                "description": "One sentence explaining the score.",
            },
        },
        "required": [
            "identifies_issue",
            "justifies_escalation",
            "no_invented_facts",
            "score",
            "comment",
        ],
    },
}

JUDGE_SYSTEM = (
    "You are evaluating the reasoning produced by a support-ticket triage agent. "
    "You are NOT re-triaging the ticket. Judge only whether the reasoning is sound, "
    "specific, and grounded in what the agent could actually know. "
    "The agent's escalation policy lists these triggers: money lost, legal threats, "
    "security concerns, angry repeat customer, revenue-expanding request. "
    "Vague justifications such as 'the customer seems frustrated' do not count as "
    "naming a trigger. Be strict but fair; do not reward length."
)


def judge_reasoning(ticket_text: str, reasoning: str, escalated: bool) -> dict:
    """Grade one reasoning string against the rubric. Returns the judgment dict."""
    client = anthropic.Anthropic()

    prompt = (
        f"TICKET:\n{ticket_text}\n\n"
        f"AGENT ESCALATED: {escalated}\n\n"
        f"AGENT REASONING:\n{reasoning}\n\n"
        "Score this reasoning using the rubric."
    )

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=500,
        system=JUDGE_SYSTEM,
        tools=[JUDGE_TOOL],
        # FORCED, unlike the agent: the judge has exactly one job and must do it.
        tool_choice={"type": "tool", "name": "record_judgment"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {"score": 0, "comment": "judge produced no structured verdict"}