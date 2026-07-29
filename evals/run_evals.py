"""Run the agent over the golden dataset and report scores.

Order matters: deterministic checks run first on every case (free), the
judge runs second and only if --judge is passed (costs an API call each).

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --judge
    python evals/run_evals.py --case adv_001
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Running a script directly puts evals/ on sys.path, not the repo root.
# Add the repo root so `src.triage` and `evals.scoring` both resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.triage.agent import run_triage_with_metrics
from evals.scoring import score_case
from evals.judges.reasoning_judge import judge_reasoning

DATASET = Path("evals/dataset/tickets.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", action="store_true", help="also run the LLM judge")
    parser.add_argument("--case", help="run a single case_id only")
    args = parser.parse_args()

    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    if args.case:
        cases = [c for c in cases if c["case_id"] == args.case]

    rows = []
    total_in = total_out = 0
    started = time.time()

    for case in cases:
        run = run_triage_with_metrics(case["ticket_text"], case["customer_id"])
        scored = score_case(case, run.result)
        total_in += run.input_tokens
        total_out += run.output_tokens

        if args.judge and run.result is not None:
            judgment = judge_reasoning(
                case["ticket_text"], run.result.reasoning, run.result.needs_human
            )
            scored["judge_score"] = judgment.get("score", 0)
            scored["judge_comment"] = judgment.get("comment", "")
        rows.append(scored)

    _report(rows, total_in, total_out, time.time() - started, args.judge)


def _report(rows, total_in, total_out, elapsed, judged):
    header = f"{'case':<10} {'type':<14} {'cat':<5} {'urg':<5} {'esc':<5} {'trig':<5} {'PASS':<6}"
    if judged:
        header += " judge"
    print(header)
    print("-" * len(header))

    def mark(b):
        return "ok" if b else "FAIL"

    for r in rows:
        line = (
            f"{r['case_id']:<10} {r['case_type']:<14} "
            f"{mark(r['category_pass']):<5} {mark(r['urgency_pass']):<5} "
            f"{mark(r['escalation_pass']):<5} {mark(r['trigger_cited']):<5} "
            f"{mark(r['deterministic_pass']):<6}"
        )
        if judged:
            line += f" {r.get('judge_score', '-')}"
        print(line)

    n = len(rows)
    passed = sum(1 for r in rows if r["deterministic_pass"])
    fns = [r["case_id"] for r in rows if r["false_negative"]]
    fps = [r["case_id"] for r in rows if r["false_positive"]]

    print()
    print(f"Decision accuracy:     {passed}/{n}")
    print(f"MISSED escalations:    {len(fns)}  {fns if fns else ''}")
    print(f"Over-escalations:      {len(fps)}  {fps if fps else ''}")

    # Per-type breakdown: a high overall score built only on easy cases is noise.
    types = sorted({r["case_type"] for r in rows})
    for t in types:
        sub = [r for r in rows if r["case_type"] == t]
        print(f"  {t:<14} {sum(1 for r in sub if r['deterministic_pass'])}/{len(sub)}")

    if judged:
        scores = [r["judge_score"] for r in rows if "judge_score" in r]
        if scores:
            print(f"Reasoning quality:     {sum(scores)/len(scores):.1f}/5 (advisory)")

    print(f"Tokens: {total_in} in / {total_out} out   Elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    main()