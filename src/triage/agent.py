"""Agentic triage: Claude chooses which lookup tools to consult, then records a triage."""

import time
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

from src.triage.schemas import TriageResult
from src.triage.tools import get_customer_history, check_known_outages

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 6  # the SAFETY stop: hard cap on loop rounds

SYSTEM_PROMPT = (
    "You are a support-ticket triage agent. Classify the ticket into a category "
    "and urgency, and decide if a human needs to handle it. You may consult the "
    "lookup tools first if customer history or outage status would change your "
    "decision. When you are confident, call record_triage exactly once. "
    "Escalate to a human (needs_human=true) when the ticket involves money lost, "
    "legal threats, security concerns, an angry repeat customer, or a "
    "revenue-expanding request such as adding seats, upgrading plans, or an "
    "enterprise renewal."
)

# All three tool definitions live here at module level so tests can import them.
# record_triage is the FINISH LINE: calling it is the agent's natural stop.
TOOL_DEFINITIONS = [
    {
        "name": "get_customer_history",
        "description": "Look up a customer's plan, prior ticket count, and recent refunds.",
        "input_schema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "check_known_outages",
        "description": "Check whether a named service currently has a known outage.",
        "input_schema": {
            "type": "object",
            "properties": {"service": {"type": "string"}},
            "required": ["service"],
        },
    },
    {
        "name": "record_triage",
        "description": "Record the final triage decision. Call exactly once, when confident.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["billing", "technical", "account", "other"]},
                "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
                "needs_human": {"type": "boolean"},
                "reasoning": {"type": "string"},
            },
            "required": ["category", "urgency", "needs_human", "reasoning"],
        },
    },
]

# Maps a tool's name (string) to the actual Python function that implements it.
TOOL_FUNCTIONS = {
    "get_customer_history": get_customer_history,
    "check_known_outages": check_known_outages,
}


@dataclass
class TriageRun:
    """One agent run: the decision plus what it cost to get there.

    Token counts are SUMMED across every API call the loop made, not taken from
    a single response. An agent re-sends the whole growing message list each
    round, so a 3-call run costs far more input than 3x the first call.
    """

    result: TriageResult | None
    input_tokens: int
    output_tokens: int
    seconds: float
    api_calls: int


def run_triage(ticket_text: str, customer_id: str) -> TriageResult | None:
    """Run the agent loop on one ticket. Returns a validated TriageResult,
    or None if the agent failed to reach a decision.

    Thin wrapper kept for existing callers; see run_triage_with_metrics.
    """
    return run_triage_with_metrics(ticket_text, customer_id).result


def run_triage_with_metrics(ticket_text: str, customer_id: str) -> TriageRun:
    """Same loop as run_triage, but also reports token usage and wall-clock time."""
    client = anthropic.Anthropic()

    input_tokens = 0
    output_tokens = 0
    api_calls = 0
    result: TriageResult | None = None
    started = time.perf_counter()

    # The conversation starts with one user message containing the ticket.
    # This list GROWS each round — it is the agent's memory of its investigation.
    messages = [
        {
            "role": "user",
            "content": f"Triage this ticket.\ncustomer_id: {customer_id}\nticket: {ticket_text}",
        }
    ]

    for _ in range(MAX_TURNS):  # the safety stop lives here
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            tool_choice={"type": "auto"},  # Claude DECIDES: a tool, or just talk
            messages=messages,
        )

        # Meter every call, including ones that end in a failure branch below —
        # a run that burned tokens and decided nothing still cost money.
        api_calls += 1
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        # ---- read stop_reason and react: this is the heart of the loop ----

        if response.stop_reason == "tool_use":
            # Claude asked to use one or more tools this round.
            tool_results = []
            decided = False
            for block in response.content:
                if block.type != "tool_use":
                    continue  # skip any thinking-out-loud text blocks

                if block.name == "record_triage":
                    # NATURAL STOP: the finish-line tool was called.
                    # Validate Claude's output through Pydantic before trusting it.
                    result = TriageResult(**block.input)
                    decided = True
                    break

                # Otherwise it's a lookup tool: run the real function.
                fn = TOOL_FUNCTIONS[block.name]
                tool_output = fn(**block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,  # quote back Claude's ID
                        "content": str(tool_output),
                    }
                )

            if decided:
                break

            # Append BOTH sides to the conversation: Claude's request, our answers.
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            # loop continues: next round Claude sees the tool results

        elif response.stop_reason == "end_turn":
            # Claude finished talking WITHOUT calling record_triage.
            # Design choice: we treat this as a failure to decide.
            break

        else:
            # "max_tokens" or anything unexpected: the reply is unreliable.
            break

    # Falling out of the loop without a result means the safety stop fired
    # (or a failure branch broke out) — result is still None in both cases.
    return TriageRun(
        result=result,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        seconds=time.perf_counter() - started,
        api_calls=api_calls,
    )