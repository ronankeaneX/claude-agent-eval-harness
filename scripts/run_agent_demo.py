"""Demo: run the triage agent on one ticket N times and print a metrics table."""

import argparse
import sys
from pathlib import Path

# Running a script directly puts scripts/ on sys.path, not the repo root.
# Add the repo root so `src.triage` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.triage.agent import run_triage_with_metrics

TICKET_TEXT = (
    "I was charged twice this month and the second charge overdrew my "
    "account. Fix this today or I'm disputing with my bank."
)
CUSTOMER_ID = "cust_002"

HEADER = f"{'run':>3}  {'category':<9} {'urgency':<8} {'human':<6} {'in_tok':>7} {'out_tok':>7} {'secs':>6}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="how many times to run the same ticket (default: 1)",
    )
    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n must be at least 1")

    print(HEADER)
    print("-" * len(HEADER))

    decisions = []  # one (category, urgency, needs_human) tuple per run
    failures = 0

    for i in range(1, args.n + 1):
        run = run_triage_with_metrics(ticket_text=TICKET_TEXT, customer_id=CUSTOMER_ID)

        if run.result is None:
            # The agent burned tokens without reaching a decision. Still worth a
            # row — the cost is real even when the answer never arrived.
            failures += 1
            category, urgency, human = "-", "-", "-"
        else:
            decisions.append(
                (run.result.category, run.result.urgency, run.result.needs_human)
            )
            category = run.result.category
            urgency = run.result.urgency
            human = str(run.result.needs_human)

        print(
            f"{i:>3}  {category:<9} {urgency:<8} {human:<6} "
            f"{run.input_tokens:>7} {run.output_tokens:>7} {run.seconds:>6.2f}"
        )

    print()
    print(agreement_line(decisions, failures, args.n))


def agreement_line(decisions: list[tuple], failures: int, total: int) -> str:
    """One sentence on whether every run reached the same three field values."""
    if failures:
        return (
            f"DISAGREE: {failures}/{total} run(s) reached no decision at all, "
            f"so the runs cannot all agree."
        )
    unique = set(decisions)
    if len(unique) == 1:
        category, urgency, human = unique.pop()
        return (
            f"AGREE: all {total} run(s) returned "
            f"category={category}, urgency={urgency}, needs_human={human}."
        )
    return (
        f"DISAGREE: {total} runs produced {len(unique)} distinct "
        f"(category, urgency, needs_human) combinations: {sorted(map(str, unique))}"
    )


if __name__ == "__main__":
    main()
