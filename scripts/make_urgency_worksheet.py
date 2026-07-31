"""Blinded worksheet for the urgency label audit (M4 step 4b-ii), version 2.

WHY V2 EXISTS
V1 asked for BAND first and DISTANCE afterwards, which let a band be chosen by
feel and the remaining fields backfilled to match. Six of seventeen entries came
back with a BAND that contradicted their own DISTANCE. V2 removes BAND from the
form entirely and DERIVES it, so that class of contradiction cannot be written.

V2 also splits a conflation in v1: DISTANCE had no way to say "a real clock, but
a distant one". A statutory deadline three weeks out is a genuine closing window
and still bands low. V1 forced that case to claim there was no clock at all.

  hours   -> high
  days    -> medium
  weeks+  -> low   (a clock exists, but it is far away)
  none    -> low   (no clock at all)

Blinding is unchanged: ticket text only, same seed, so case numbering matches v1.

Two modes, run from the repo root:

    python scripts/make_urgency_worksheet.py            # write the worksheet
    python scripts/make_urgency_worksheet.py --derive   # validate + derive bands
"""

import json
import random
import sys
from pathlib import Path

SEED = 20260730  # unchanged from v1: same shuffle, same case numbers
DATASET = Path("evals/dataset/tickets.json")
OUTDIR = Path("..") / "urgency-audit"
WORKSHEET = OUTDIR / "worksheet-v2.txt"  # never overwrites the v1 file
KEYFILE = OUTDIR / "key.json"

CLOCKS = {
    "ongoing accrual",
    "closing window",
    "active exploitation",
    "stated deadline",
    "none",
    "unresolved",
}

# A clock whose kind is defined by a date must say WHICH date.
NEEDS_WHAT = {"closing window", "stated deadline"}

DISTANCES = {"hours", "days", "weeks+", "none"}

BAND_FROM_DISTANCE = {
    "hours": "high",
    "days": "medium",
    "weeks+": "low",
    "none": "low",
}

FIELDS = ("CLOCK", "WHAT", "DISTANCE", "WHY")

HEADER = """URGENCY LABEL AUDIT WORKSHEET (v2)
seed {seed} | {n} cases | ticket text only, shuffled

There is no BAND field. The band is derived from DISTANCE, so it cannot
disagree with the rest of the answer.

  CLOCK     ongoing accrual | closing window | active exploitation
            | stated deadline | none | unresolved
  WHAT      only for closing window / stated deadline: WHAT closes, and
            WHEN. No date means it is not a window. Otherwise leave blank.
  DISTANCE  hours | days | weeks+ | none
            (weeks+ means a real clock that is far away)
  WHY       one line, about time only

Not factors: tone, harm already completed, whether a human is needed,
absolute magnitude, revenue, account tier.

Test the WHY: with the ticket text deleted, could a reader still tell
roughly how much time is left? If not, rewrite it.
"""


def build() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    pairs = [(c["case_id"], c["ticket_text"]) for c in cases]
    random.Random(SEED).shuffle(pairs)

    OUTDIR.mkdir(parents=True, exist_ok=True)

    out = [HEADER.format(seed=SEED, n=len(pairs)), "=" * 70, ""]
    for i, (_case_id, text) in enumerate(pairs, start=1):
        out += [
            f"--- {i:02d} " + "-" * 60,
            text.strip(),
            "",
            "    CLOCK    :",
            "    WHAT     :",
            "    DISTANCE :",
            "    WHY      :",
            "",
        ]

    WORKSHEET.write_text("\n".join(out), encoding="utf-8")

    key = {f"{i:02d}": cid for i, (cid, _text) in enumerate(pairs, start=1)}
    KEYFILE.write_text(json.dumps(key, indent=2), encoding="utf-8")

    print(f"worksheet -> {WORKSHEET.resolve()}")
    print(f"key       -> {KEYFILE.resolve()}")
    print()
    print("Case numbers match v1. The v1 worksheet is left untouched.")
    print("Do not open the key until every case is filled in.")


def parse(path: Path) -> dict:
    """Read the filled worksheet into {case_number: {field: value}}."""
    entries: dict = {}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("--- "):
            num = line.split()[1]
            current = {}
            entries[num] = current
            continue
        if current is None:
            continue
        head, sep, value = line.partition(":")
        if sep and head.strip() in FIELDS:
            current[head.strip()] = value.strip()
    return entries


def check(entry: dict) -> list:
    """Return a list of problems with one entry. Empty list means it is clean."""
    problems = []
    clock = entry.get("CLOCK", "").lower()
    what = entry.get("WHAT", "").strip()
    distance = entry.get("DISTANCE", "").lower()
    why = entry.get("WHY", "").strip()

    if not clock:
        problems.append("CLOCK is empty")
    elif clock not in CLOCKS:
        problems.append(f"CLOCK '{clock}' is not one of the allowed values")

    if not distance:
        problems.append("DISTANCE is empty")
    elif distance not in DISTANCES:
        problems.append(f"DISTANCE '{distance}' is not one of the allowed values")

    if not why:
        problems.append("WHY is empty")

    if clock in NEEDS_WHAT and (not what or what.lower() in {"n/a", "na", "-"}):
        problems.append(
            f"CLOCK is '{clock}' but WHAT does not name what closes and when"
        )

    if clock == "none" and distance and distance != "none":
        problems.append("CLOCK is 'none' but DISTANCE claims time is running")

    if clock not in {"none", "unresolved", ""} and distance == "none":
        problems.append(f"CLOCK is '{clock}' but DISTANCE says there is no clock")

    return problems


def derive() -> None:
    if not WORKSHEET.exists():
        sys.exit(f"not found: {WORKSHEET.resolve()}\nRun without --derive first.")

    entries = parse(WORKSHEET)
    if not entries:
        sys.exit("no case blocks found; is this the right file?")

    clean, flagged = [], []
    for num in sorted(entries):
        problems = check(entries[num])
        if problems:
            flagged.append((num, problems))
        else:
            band = BAND_FROM_DISTANCE[entries[num]["DISTANCE"].lower()]
            clean.append((num, band, entries[num]))

    print(f"{len(clean)} clean, {len(flagged)} flagged, {len(entries)} total")
    print()

    if clean:
        print("DERIVED BANDS")
        for num, band, entry in clean:
            print(f"  {num}  {band:<6}  {entry['CLOCK']:<20}  {entry['DISTANCE']}")
        print()

    if flagged:
        print("FLAGGED (no band derived)")
        for num, problems in flagged:
            print(f"  {num}")
            for p in problems:
                print(f"       {p}")
        print()
        print("Fix these in the worksheet and re-run --derive.")


if __name__ == "__main__":
    if "--derive" in sys.argv:
        derive()
    else:
        build()
