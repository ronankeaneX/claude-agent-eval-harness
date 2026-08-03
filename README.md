# claude-agent-eval-harness

A support-ticket triage agent, and the evaluation harness that measures whether it
can be trusted.

The agent is small on purpose. The harness is the point. Most of the work here went
into building a measuring instrument you can believe, and then finding out what it
says.

**Measured, not projected:** 0 missed escalations across 51 runs at temperature 0,
with false negatives reported separately from false positives. Deterministic pass
rate is 8 of 17 cases on a suite built to be hard: 11 of the 17 are ambiguous,
adversarial, or out of scope. Both numbers come from the same sweep, and the second
is why the first is worth quoting.

---

## What the agent does

Reads a support ticket and returns three fields plus its reasoning:

| Field | Values | Scored |
|---|---|---|
| `category` | billing, technical, account, other | exact match, acceptable sets on ambiguous cases |
| `urgency` | low, medium, high | exact match, acceptable sets on ambiguous cases |
| `needs_human` | true / false | strict, always |

It is an agent, not a workflow: it decides which tools to call and when to stop,
rather than following a fixed sequence. Three tools (customer history, known
outages, and a `record_triage` finish-line tool), a turn cap, and a system prompt
defining five escalation triggers.

## What the harness does

- Runs every case `n` times and votes, because a single run is not a measurement
- Pins temperature to 0 so a real change can be told apart from run-to-run noise
- Scores structured fields deterministically, and reasoning quality with an LLM
  judge that is reported prominently and never gates
- Reports failure *direction*, not just failure counts
- Splits missed escalations from over-escalations, and never blends them

---

## Running it

Python 3.11+ and an Anthropic API key.

```bash
git clone https://github.com/ronankeaneX/claude-agent-eval-harness
cd claude-agent-eval-harness

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then:

```bash
# one ticket, end to end, with tool calls printed
python scripts/run_agent_demo.py

# same ticket several times, to see the variance the harness controls for
python scripts/run_agent_demo.py --n 5

# full sweep: 17 cases, 3 runs each
python evals/run_evals.py

# one case only, for a targeted diagnostic
python evals/run_evals.py --case easy_003 --n 3

# add the advisory reasoning judge
python evals/run_evals.py --judge

# tests (no API calls, no cost)
pytest
```

A full sweep at the default `--n 3` is 51 agent calls, about 9.6 minutes and
roughly 127k tokens. Targeted `--case` runs exist so you are not spending a sweep
to answer a single question.

---

## Layout

```
src/triage/          agent loop, tool definitions, Pydantic schemas
evals/               scoring, harness, dataset
evals/judges/        LLM reasoning judge (advisory)
scripts/             demo, smoke test, audit tooling
tests/               schema drift tripwire
docs/                urgency policy, label audit artifacts
```

---

## Design decisions

Each of these had an alternative. The alternative is stated, and so is why it lost.

**Agent, not workflow.** A workflow would be cheaper and more predictable. The line
between them is not linear versus branching, because workflows branch too. It is
who decides the next step. This repo exists to show the agent case, so the agent
picks its own tools and its own stopping point, and the harness is what makes that
safe to claim.

**Smallest version that proves the point.** Three tools, 17 cases, one model. Every
addition beyond that would have been scope, not evidence. What is here is what the
measurement needs.

**Temperature is a caller parameter, not an agent constant.** The harness pins it to
0 for repeatability. Production temperature stays an open product decision.
Hardcoding 0 inside the agent lets the test harness make a product call by accident.
Instrument settings and product settings stay in separate hands.

**Temperature 0 and n-run voting are a pair, not alternatives.** Temperature 0
shrinks output variance. It does not remove it. Measured here: about 18% of case
verdicts flipped between runs at temperature 1.0. At 0 that collapsed to four cases and five field flips in total. Smaller, not
gone, so the voting layer stays.

**Voting is per case, never per field.** A per-field majority can assemble a passing
composite that no single run produced, which gates on a synthetic agent instead of
the real one. Per-field agreement is a diagnostic only. Even ties fail: no majority
means no verdict to gate on.

**`needs_human` is strict, and its two failure directions never get blended.** A
customer who needed a human and did not get one is a safety signal. A human who
looked at something they did not need to is a cost signal. One number for both
trains the reader to skim past the one that matters, so they get separate lines and
separate severities.

**A case that fails to escalate on even one run of n is reported as a missed
escalation,** even where it passes the gate on majority. In production that is a
probabilistic miss, not a pass.

**The judge is advisory and never gates.** The best argument for that is in the
results: one case scores 1 out of 5 on reasoning while passing every deterministic
check. Right answer, weakest reasoning in the suite. Worth surfacing loudly, not
worth failing a build over.

**Schema duplication is accepted and protected by a test.** The allowed values exist
twice, once in the tool's JSON Schema enum and once as a Pydantic `Literal`.
`tests/test_schema_sync.py` fails if they drift. The drift is asymmetric and worth
knowing: a `Literal` *narrower* than the enum raises a loud `ValidationError`, while
a *wider* one causes silent misclassification, because the model is constrained by
the JSON enum and cannot emit the new value at all.

**Acceptable-value sets are fixed when the case is written, and never widened to
make a run pass.** Three of 17 cases are explicitly ambiguous and accept more than
one value. Widening a set after seeing a failure is moving the standard to fit the
result. So is rerunning a failed case and reporting the best run, or raising `n`
until something passes.

**Metrics are committed before the run, not chosen after it.** Each prompt change is
measured as a deliberate before and after against a frozen baseline, one change at a
time. Predictions get written down first, because a prediction recorded afterward is
rationalization. One of the predictions in this repo missed, and the reason it
missed is the most useful thing in the results.

**The dataset is part of the instrument.** Labels are not ground truth handed down
from outside. They were authored, and they can be wrong. So changing a label voids a
baseline exactly as changing the scorer would, and label adjudication has to be
blind to model behavior or it is just fitting the answer key to the output.

---

## What the evals found

Three findings. Only one is about the agent.

**1. The labels had bugs, not just the prompt.**

Urgency failed on 8 of 17 cases. Reading the label rationales, six of them never
argue urgency at all. They justify escalation, and look like they took an urgency
value as a default while the author was thinking about something else. The cases
that pass urgency consistently are the ones whose rationales reason about it
explicitly.

Writing a prompt rubric to make the agent match those six would have been fitting
the prompt to weak labels. That is what produced the urgency policy in
`docs/urgency-policy.md`, and it is the finding worth reading first: the evals found
defects in the answer key. A pass rate cannot tell you that.

**2. The elicitation form was itself an instrument.**

Adjudicating the labels needed a written urgency policy and then a blind pass over
all 17 tickets. The first version of that worksheet asked for the band first and the
supporting detail after. Six of 17 entries came back with a band that contradicted
their own stated time distance, and one clock type absorbed nine of 17 cases as a
catch-all.

The second version removed the band from the form and derived it from the time
distance instead. Same person, same policy, same tickets: every severity and revenue
argument disappeared. A badly ordered form manufactures findings the same way an
uncalibrated judge does. Both worksheets are committed in `docs/audits/` as evidence.

**3. A rubric that reads clearly is not the same as a rubric that holds.**

The urgency policy failed to keep its own author inside the time-sensitivity frame
while he worked the tickets, one screen away from the document. That is a usability
property of the instruction, and it predicts something about how the same text will
fare in a single agent pass.

**The instrument also caught itself manufacturing a result.** An earlier judge run at
temperature 1.0 produced a two-case finding. Re-run pinned at 0, one case held and
the other evaporated, and the fabricated one looked exactly like the real one. Any
finding taken with an uncalibrated instrument is provisional until it is re-taken
with a calibrated one.

---

## Baseline

Taken 2026-07-30. Instrument: temperature 0, `--n 3`, per-case voting, even ties
fail, judge advisory.

| Measure | Result |
|---|---|
| Deterministic pass | 8 / 17 |
| Missed escalations, majority level | 0 |
| Missed escalations, any single run of 51 | 0 |
| Over-escalations | 3 |
| No-decision (safety stop) runs | 0 of 51 |
| Judge, reasoning quality | 2.7 / 5 across 17 cases |
| Field flips at temperature 0 | category 2/17, urgency 1/17, needs_human 1/17, trigger_cited 1/17 |

Cost and latency, measured rather than projected:

| | |
|---|---|
| Input tokens | 106,483 |
| Output tokens | 20,725 |
| Wall clock | 574.5s (9.6 min) for 51 runs |
| Per run | 11.3s average |

Latency is nondeterministic even at temperature 0, which matters for any CI timeout
built on top of this. A single-case smoke test extrapolated to a 13-minute sweep,
about 35% high, so one case is a poor basis for a pace estimate.

The raw stdout of this sweep was not retained. The figures above were transcribed
from it and are the authoritative record. Re-running would produce a new baseline
rather than evidence for this one, so the gap is documented instead of papered over.

---

## Known gaps

- **No CI and no regression gate yet.** A 51-run sweep per push is untenable and the
  reduced-sweep design is not made. The baseline is compared by hand today.
- **Trigger citation is a blunt keyword match.** It checks whether the agent named
  one of five known trigger strings. It does not check whether the trigger applies.
- **The judge is uncalibrated.** Treat 2.7/5 as a signal to read the reasoning, not
  as a quality score. Verbosity bias and self-preference are known judge failure
  modes and neither is controlled for here.
- **Urgency is unmeasured against the current policy.** `docs/urgency-policy.md` was
  written and validated but never inserted into the system prompt and never swept, so
  its effect is unknown. A pre-registered prediction of +4 cases was recorded before
  the label finding and never tested.
- **17 cases is a small suite.** Deliberately weighted toward ambiguous, adversarial,
  and out-of-scope tickets, because an all-easy suite scores 96% and predicts
  nothing. Still 17 cases.

---

## Non-goals

Not a production triage system. No queue integration, no SLA mapping, no routing, no
persistence. The customer and outage data is fixture data.

---

## License

MIT. See [LICENSE](LICENSE).
