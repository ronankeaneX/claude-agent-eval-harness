"""Run the agent over the golden dataset and report scores.

Order matters: deterministic checks run first on every case (free), the
judge runs second and only if --judge is passed (costs an API call each).

Every case runs --n times at temperature=0, and its verdict is a MAJORITY VOTE
over those runs. Voting is PER CASE on the whole deterministic result — NOT a
composite triage assembled from per-field majorities. That distinction matters:
per-field majorities could manufacture a (category, urgency, needs_human)
combination that no single run ever produced, and then score it.

temperature=0 narrows run-to-run variance but does not eliminate it, so the flip
diagnostics measure the INSTRUMENT, not the agent. They never gate a build.

Usage:
    python evals/run_evals.py
    python evals/run_evals.py --n 5
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
# _matches is imported so the DISPLAY of a mismatch agrees with the scorer's
# own list-vs-scalar semantics. Reimplementing it here could show a field as
# mismatched that the scorer counted as a pass.
from evals.scoring import score_case, _matches
from evals.judges.reasoning_judge import judge_reasoning

# Resolved from __file__, not cwd, for the same reason as the sys.path line
# above: the harness must not depend on where it was invoked from.
DATASET = Path(__file__).resolve().parent / "dataset" / "tickets.json"

# Fields whose run-to-run stability we track. Pass/fail is the VERDICT; these
# are the instrument's reliability, reported separately and never gating.
FLIP_FIELDS = ["category", "urgency", "needs_human", "trigger_cited"]

# The three fields the agent actually chooses a VALUE for. trigger_cited is
# excluded: it is a derived check, not something the agent emits.
VALUE_FIELDS = ["category", "urgency", "needs_human"]

# Compact labels for the flips column.
SHORT = {
    "category": "cat",
    "urgency": "urg",
    "needs_human": "esc",
    "trigger_cited": "trig",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=3, help="runs per case (default: 3)")
    parser.add_argument("--judge", action="store_true", help="also run the LLM judge")
    parser.add_argument("--case", help="run a single case_id only")
    args = parser.parse_args()

    if args.n < 1:
        parser.error("--n must be at least 1")

    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    if args.case:
        cases = [c for c in cases if c["case_id"] == args.case]
        if not cases:
            parser.error("no case with case_id " + repr(args.case))

    rows = []
    total_in = total_out = 0
    started = time.time()

    for case in cases:
        runs = []  # one scored dict per run
        values = {f: [] for f in FLIP_FIELDS}  # actual VALUES, for flip detection
        judged_result = None  # the first run that actually produced a decision
        judged_index = None  # 1-based index of that run, for the diagnostics

        for i in range(args.n):
            run = run_triage_with_metrics(
                case["ticket_text"],
                case["customer_id"],
                temperature=0,  # instrument mode: repeatability required
            )
            total_in += run.input_tokens
            total_out += run.output_tokens

            scored = score_case(case, run.result)
            runs.append(scored)

            # The judge scores the FIRST run that actually decided. Pinning it to
            # run 1 would silently skip the judge whenever run 1 happened to hit
            # the safety stop — losing the advisory signal for a case that did
            # decide on a later run.
            if judged_result is None and run.result is not None:
                judged_result = run.result
                judged_index = i + 1  # 1-based: runs are described as run 1..n

            # A None result is recorded as a DISTINCT value, never folded into
            # False: "never decided" and "decided no" are different failures,
            # and collapsing them would hide safety-stop bugs.
            if run.result is None:
                values["category"].append(None)
                values["urgency"].append(None)
                values["needs_human"].append(None)
            else:
                values["category"].append(run.result.category)
                values["urgency"].append(run.result.urgency)
                values["needs_human"].append(run.result.needs_human)
            values["trigger_cited"].append(scored["trigger_cited"])

        row = _aggregate(case, runs, values)
        # Recorded even when --judge is off, so the diagnostics can always say
        # which run the judge WOULD have read. None means no run ever decided.
        row["judge_run"] = judged_index
        rows.append(row)

        # The judge runs ONCE per case, on the first DECIDING run — not n times.
        # It is advisory, so paying n times for it buys nothing that gates.
        # Skipped only when ALL n runs returned None: there is no reasoning to read.
        if args.judge and judged_result is not None:
            judgment = judge_reasoning(
                case["ticket_text"], judged_result.reasoning, judged_result.needs_human
            )
            row["judge_score"] = judgment.get("score", 0)
            row["judge_comment"] = judgment.get("comment", "")

    _report(rows, total_in, total_out, time.time() - started, args.judge, args.n)


def _majority(flags: list) -> bool:
    """True when STRICTLY more than half the runs passed.

    An even n that ties FAILS: an instrument that cannot make up its mind has
    not demonstrated a pass.
    """
    return sum(1 for f in flags if f) * 2 > len(flags)


def _aggregate(case: dict, runs: list, values: dict) -> dict:
    """Collapse n runs into one row: majority verdict plus flip diagnostics."""
    row = {
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        # Per-field pass COUNTS are for the table only — not the verdict.
        "category_passes": sum(1 for r in runs if r["category_pass"]),
        "urgency_passes": sum(1 for r in runs if r["urgency_pass"]),
        "escalation_passes": sum(1 for r in runs if r["escalation_pass"]),
        "trigger_passes": sum(1 for r in runs if r["trigger_cited"]),
        # THE VERDICT: one majority vote on the whole deterministic result.
        "deterministic_pass": _majority([r["deterministic_pass"] for r in runs]),
        # Majority-level escalation failures keep the headline numbers honest...
        "false_negative": _majority([r["false_negative"] for r in runs]),
        "false_positive": _majority([r["false_positive"] for r in runs]),
        # ...while ANY-run failures catch intermittent ones a vote would absorb.
        "any_false_negative": any(r["false_negative"] for r in runs),
        "any_false_positive": any(r["false_positive"] for r in runs),
        "none_count": sum(1 for r in runs if r["note"] == "agent returned no decision"),
    }
    # A field FLIPPED if it did not settle on one value across all n runs.
    row["flipped"] = [f for f in FLIP_FIELDS if len(set(values[f])) > 1]

    # DIAGNOSTIC ONLY: what the label asked for vs what the agent actually said.
    # A fail count tells you a field was wrong; these tell you which way it was
    # wrong, which is what a prompt fix has to be aimed at.
    row["expected"] = {
        "category": case["expected_category"],
        "urgency": case["expected_urgency"],
        "needs_human": case["expected_needs_human"],
    }
    row["actual"] = {f: list(values[f]) for f in VALUE_FIELDS}
    return row


def _report(rows, total_in, total_out, elapsed, judged, n):
    total = len(rows)

    print("Runs per case: %d   temperature=0   verdict = majority of runs" % n)
    print()

    header = (
        f"{'case':<10} {'type':<14} {'cat':<6} {'urg':<6} {'esc':<6} "
        f"{'trig':<6} {'PASS':<6} {'flips':<17}"
    )
    if judged:
        header += " judge"
    print(header)
    print("-" * len(header))

    for r in rows:
        flips = ",".join(SHORT[f] for f in r["flipped"]) or "-"
        cat = "%d/%d" % (r["category_passes"], n)
        urg = "%d/%d" % (r["urgency_passes"], n)
        esc = "%d/%d" % (r["escalation_passes"], n)
        trig = "%d/%d" % (r["trigger_passes"], n)
        verdict = "ok" if r["deterministic_pass"] else "FAIL"
        line = (
            f"{r['case_id']:<10} {r['case_type']:<14} {cat:<6} {urg:<6} "
            f"{esc:<6} {trig:<6} {verdict:<6} {flips:<17}"
        )
        if judged:
            line += " " + str(r.get("judge_score", "-"))
        print(line)

    passed = sum(1 for r in rows if r["deterministic_pass"])
    fns = [r["case_id"] for r in rows if r["false_negative"]]
    fps = [r["case_id"] for r in rows if r["false_positive"]]

    print()
    print(f"Decision accuracy:     {passed}/{total}   (majority vote per case)")
    print(f"MISSED escalations:    {len(fns)}  {fns if fns else ''}")
    print(f"Over-escalations:      {len(fps)}  {fps if fps else ''}")

    # Per-type breakdown: a high overall score built only on easy cases is noise.
    for t in sorted({r["case_type"] for r in rows}):
        sub = [r for r in rows if r["case_type"] == t]
        sub_passed = sum(1 for r in sub if r["deterministic_pass"])
        print(f"  {t:<14} {sub_passed}/{len(sub)}")

    _diagnostics(rows, total, n, judged)
    _confusion(rows)

    if judged:
        scores = [r["judge_score"] for r in rows if "judge_score" in r]
        if scores:
            print()
            avg = sum(scores) / len(scores)
            print(
                f"Reasoning quality:     {avg:.1f}/5 "
                f"(advisory, {len(scores)}/{total} cases, first deciding run)"
            )

    print()
    # Judge tokens are NOT included: judge_reasoning returns only its verdict
    # dict, with no usage data to add up.
    print(f"Agent tokens: {total_in} in / {total_out} out over {total * n} runs")
    print(f"Elapsed: {elapsed:.1f}s")


def _fmt(v) -> str:
    """None is the agent never deciding — say so rather than printing 'None'."""
    return "NO-DECISION" if v is None else str(v)


def _tally(vals: list) -> str:
    """Values in first-seen order with counts: 'high x2, medium x1'."""
    ordered = []
    for v in vals:
        for i, (seen, count) in enumerate(ordered):
            if seen == v:
                ordered[i] = (seen, count + 1)
                break
        else:
            ordered.append((v, 1))
    return ", ".join(f"{_fmt(v)} x{c}" for v, c in ordered)


def _wrong(field: str, expected, actuals: list) -> bool:
    """Did the agent miss on at least one run? Mirrors the scorer exactly.

    needs_human uses plain equality and category/urgency use _matches, because
    that is what score_case does. A None actual never matches, so a
    no-decision run always counts as a miss.
    """
    if field == "needs_human":
        return any(a != expected for a in actuals)
    return any(not _matches(expected, a) for a in actuals)


def _confusion(rows):
    """Expected vs actual per field. DIAGNOSTIC ONLY — gates nothing.

    Only fields that missed on >=1 run are printed: a field that matched every
    run carries no diagnostic information and would bury the ones that did not.
    """
    print()
    print("--- CONFUSION DIRECTION (diagnostic only: never gates) ---")
    print("  Shown where the agent's value missed on at least one run.")
    print("  'gate' is the case's majority verdict, repeated for context only.")
    print()

    any_shown = False
    for r in rows:
        gate = "ok  " if r["deterministic_pass"] else "FAIL"
        for field in VALUE_FIELDS:
            expected = r["expected"][field]
            actuals = r["actual"][field]
            if not _wrong(field, expected, actuals):
                continue
            any_shown = True
            print(
                f"  {r['case_id']:<10} {gate}  {field:<12} "
                f"expected={_fmt(expected):<22} actual={_tally(actuals)}"
            )

    if not any_shown:
        print("  (nothing to show: every field matched on every run)")


def _diagnostics(rows, total, n, judged=False):
    """Instrument reliability. Advisory only — none of this gates a build."""
    print()
    print("--- DIAGNOSTICS (advisory: never gates) ---")

    if n < 2:
        print("  Flip rates need --n 2 or more; one run cannot disagree with itself.")
    else:
        for f in FLIP_FIELDS:
            flipped = [r["case_id"] for r in rows if f in r["flipped"]]
            pct = (100.0 * len(flipped) / total) if total else 0.0
            print(
                f"  {f:<14} flipped in {len(flipped)}/{total} cases "
                f"({pct:.0f}%)  {flipped if flipped else ''}"
            )

        # needs_human gets its own callout: an intermittent escalation miss is a
        # SAFETY signal, and a majority vote is designed to absorb exactly that.
        nh_fn = [
            r["case_id"]
            for r in rows
            if "needs_human" in r["flipped"] and r["any_false_negative"]
        ]
        nh_fp = [
            r["case_id"]
            for r in rows
            if "needs_human" in r["flipped"] and r["any_false_positive"]
        ]
        print()
        print("  needs_human flips, split by DIRECTION:")
        print(
            f"    false-NEGATIVE flips (failed to escalate on >=1 run): "
            f"{len(nh_fn)}  {nh_fn if nh_fn else ''}"
        )
        print(
            f"    false-POSITIVE flips (escalated when it should not):  "
            f"{len(nh_fp)}  {nh_fp if nh_fp else ''}"
        )

    # Failures the majority vote swallowed. Called out loudly on purpose.
    hidden = [
        r["case_id"] for r in rows if r["any_false_negative"] and not r["false_negative"]
    ]
    if hidden:
        print()
        print(f"  WARNING: escalation missed on >=1 run but PASSED by majority: {hidden}")
        print("           A vote is the right verdict for scoring, not for safety review.")

    nones = [(r["case_id"], r["none_count"]) for r in rows if r["none_count"]]
    total_nones = sum(c for _, c in nones)
    print()
    print(
        f"  No-decision runs (result None): {total_nones} of {total * n} runs  "
        f"{nones if nones else ''}"
    )

    if judged:
        # Which run the judge actually read. Anything other than run 1 means an
        # earlier run returned None, so this doubles as a no-decision breadcrumb.
        # .get(): reporting must never crash a run that already paid for its
        # API calls, even if a row reaches here without the key.
        later = [
            (r["case_id"], r.get("judge_run"))
            for r in rows
            if r.get("judge_run") not in (None, 1)
        ]
        skipped = [r["case_id"] for r in rows if r.get("judge_run") is None]
        print()
        print("  Judge input: first DECIDING run per case")
        if later:
            print(f"    judged on a LATER run (earlier run(s) None): {later}")
        else:
            print("    every judged case used run 1")
        print(
            f"    NOT judged (all {n} runs returned None): "
            f"{len(skipped)}  {skipped if skipped else ''}"
        )


if __name__ == "__main__":
    main()
