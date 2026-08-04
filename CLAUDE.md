# CLAUDE.md — claude-agent-eval-harness

## What this project is
Support-ticket triage AGENT (not workflow) + evaluation harness.
Portfolio repo for Ronan Keane (applied AI / contract positioning). The repo
exists to demonstrate agent design and measurement discipline: a real agentic
loop, a golden dataset, two-track scoring, and an instrument trustworthy enough
that a movement in the score means something.
Build quality over speed. Do not compress work to hit a date.

## Dataset shape (confirmed on disk)
Top-level list of case objects. Field names, exactly:
  case_id, ticket_text, customer_id, expected_category, expected_urgency,
  expected_needs_human, label_rationale
There is NO nested `labels` object. Ambiguous cases carry LIST-valued
expectations (e.g. amb_001 expected_urgency accepts ['medium','high']), so any
code or display that compares expected vs actual must reuse the scorer's
`_matches` rather than reimplementing comparison.

## Tech decisions (settled — do not relitigate)
- Python for everything (single toolchain; TS port is future work)
- Structured output via tool use; agent uses tool_choice "auto", smoke test and
  the LLM judge both use FORCED tool choice (single job, must be done)
- Agent (Option B) over workflow (Option A): repo exists to showcase agentic skill
- Pydantic for Python-side validation; Literal mirrors the API enum
- Schema duplication (JSON enum vs Literal): accepted, protected by the sync test
  in tests/test_schema_sync.py. TOOL_DEFINITIONS lives at module level in
  src/triage/agent.py so tests can import it without triggering API calls.
- TriageRun metrics dataclass lives in agent.py, not schemas.py: schemas.py holds
  shapes that cross the wire and get validated; TriageRun is local bookkeeping.
- Model: claude-sonnet-4-6
- Temperature is a CALLER parameter, not an agent constant. BOTH run_triage() and
  run_triage_with_metrics() take temperature=None (omit the param, API default
  applies) or an explicit value; None must never be sent to the API, so build
  sampling kwargs conditionally. There is NO literal temperature anywhere in
  agent.py, by design — the value arrives from whoever is calling.
  The eval harness and the judge pin it to 0 because instruments must be
  repeatable; production temperature remains an OPEN PRODUCT DECISION.
  Rationale: hardcoding 0 inside the agent lets the test harness make a product
  decision by accident. Instrument setting and product setting stay in separate
  hands. README one-liner: "Temperature is a caller parameter, not an agent
  constant — the eval harness pins it to 0 for repeatability; production behavior
  remains an open product decision."
- The JUDGE hardcodes temperature=0 rather than parameterizing it. Option B
  applies to the AGENT because the agent has a production life to protect; the
  judge is instrument-only and has no product decision at stake. The principle
  is "don't let the harness make product decisions," not "always parameterize."
  Pinning the judge makes it reproducible without making it correct — correctness
  is handled by the judge being advisory and never gating.
- Voting unit: PER-CASE for the gate. Never gate on a per-field composite,
  because a composite can pass while no individual run passed — that gates on a
  synthetic agent instead of the real one. Per-field agreement/flip rates are
  recorded as DIAGNOSTICS only.
- Even ties FAIL. No majority means no verdict to gate on.
- None results (safety stop or failure to decide) count as FAILED runs for
  voting, and are a DISTINCT value in flip detection — never folded into False.
  "Never decided" is a loop/safety-stop defect; "decided no" is a judgment
  defect. In the confusion-direction readout None prints as NO-DECISION, never
  as the literal None, which would read as if the agent chose null.
- THE DATASET IS PART OF THE INSTRUMENT. Labels are the answer key; the answer
  key is measuring apparatus, not system under test. Changing ANY label voids the
  current baseline and requires a re-baseline before further deltas mean
  anything. Price the ~10 min sweep into any label decision.
- LABEL ADJUDICATION MUST BE BLIND to agent behavior. Decide a label on its own
  merits, in writing, BEFORE looking at what the agent chose on that case.
  Deciding afterward is fitting the answer key to the behavior — same family as
  widening acceptable-value sets to make a run pass. If agent values have already
  been seen, say so and treat the adjudication as contaminated.
- URGENCY IS ANCHORED TO TIME SENSITIVITY (decided, pending label audit).
  Rejected: consequence severity (collapses into needs_human — two fields
  measuring one thing) and observable ticket features (a lookup table, not
  judgment, which undercuts what this repo demonstrates).
  needs_human answers WHO handles it; urgency answers WHEN. All four quadrants
  must be populatable, which is the test that two fields measure different things:
    not urgent / no human  — feature question
    urgent    / no human   — password reset blocking a live demo
    not urgent / human     — contract language review
    urgent    / human      — payment failing now on an enterprise account
  Anchor phrase: "how fast does this get worse if nobody touches it."
  Hours = high, days = medium, no time pressure = low.
  CAVEAT: if the label audit shows the labels encode SEVERITY rather than time
  sensitivity, time-sensitivity is still the better design but adopting it means
  changing labels, which voids the baseline. Decide with that cost visible.
- needs_human scored STRICTLY, always. False negatives (missed escalations)
  reported SEPARATELY from false positives — never blended into one number.
  This extends to the voting layer: a case that fails to escalate on even 1 of n
  runs is a probabilistic missed escalation in production and must appear in the
  false-negative diagnostics even when it passes the gate on majority.
- WARNING vs NOTE severity split. WARNING is RESERVED for the false-NEGATIVE
  direction: a customer who needed a human did not get one — a SAFETY signal.
  The false-POSITIVE direction gets a distinct lower-severity NOTE: a human
  looked at something they did not need to — a COST signal. Equal visual weight
  trains the reader to skim past the one that matters.
- Acceptable-value LISTS allowed on category/urgency for explicitly ambiguous
  cases only (3 of 17). Sets fixed at authoring time, NEVER widened to make a
  run pass. Disagreement means either the agent is wrong or the label is wrong.
- No vote-shopping: never rerun a failed case and report the best run, and never
  raise n until a case passes.
- Every dataset case carries a label_rationale.
- Fifth escalation trigger: revenue-expanding requests. adv_005 is its matched
  negative test (seat REDUCTION must not fire it).
- M3 Option A: deterministic field checks GATE the build; the LLM judge is
  advisory — reported prominently but never fails a build.
- Judge runs ONCE per case even under n-run voting, scoring the first NON-NONE
  run's output and recording which run index was judged; skipped only when ALL n
  runs are None.
- Trigger-citation check promoted from judge to deterministic (five triggers are
  known strings). Blunt keyword match — acknowledge in README non-goals.
- Unknown --case ID exits 2 rather than reporting 0/0. An instrument must not
  report a clean result for a measurement it never took.
- DIAGNOSTIC RUNS ARE TARGETED, NOT FULL SWEEPS. To check n specific cases use
  `--case <id> --n 3` per case (~4 agent calls each, ~2 min, ~8k tokens for four
  cases) instead of a 51-run sweep (9.6 min, ~106k tokens). Full sweeps are for
  measuring deltas against the baseline, not for answering diagnostic questions.

## Curriculum state
MARKERS: [x] done  [~] not done, not scheduled  [!] closed but flagged, read the entry
         [ ] open
- [x] M0: Scaffold — venv, .env hygiene, smoke test w/ forced tool use
- [x] M0b: GitHub remote connected, repo public and verified (no .env)
- [x] M1a: schemas.py — Pydantic models, Literal validation confirmed via REPL
- [x] M1b: tools.py — FAKE_CUSTOMERS/FAKE_OUTAGES stubs, structured not-found errors
- [x] M1c: agent.py — the loop, verified end-to-end.
- [x] M1d: tests/test_schema_sync.py — drift tripwire, RED then GREEN.
- [x] M2: evals/dataset/tickets.json — 17 cases (6 easy, 4 ambiguous,
      5 adversarial, 2 out-of-scope). Escalation split ~50/50.
- [x] M3: evals/scoring.py + evals/judges/reasoning_judge.py + evals/run_evals.py.
      Both tracks running.
- [ ] M4: reliability first, THEN prompt work, THEN gate/CI/README.
      - [x] step 1: temperature parameterized as a caller argument (Option B).
            run_evals.py:47 and reasoning_judge.py:79 pin 0.
            Near-miss worth remembering: the parameter existed for one turn while
            neither caller passed it — a sweep then would have LOOKED measured and
            sampled at 1.0.
            DELIBERATE: scripts/run_agent_demo.py stays at API default so its --n
            flag demonstrates the variance the harness controls for.
      - [x] step 2: --n majority voting (default 3), PER-CASE. Even ties fail.
            None distinct from False. Diagnostics: per-field flip rates +
            needs_human FN/FP split + WARNING on concealed misses.
            LESSON: Claude Code's PROSE described judge selection as "run 1's
            output," which read as run-1-only; the CODE was correct (first
            non-None). Verify against disk, not against the summary.
      - [x] step 3: baseline 8/17 taken 2026-07-30. See frozen reference below.
            Habit worth keeping: a live single-case smoke test ran BEFORE the full
            sweep because the voting code had only been exercised against offline
            fakes. Cheap validation of a new code path before spending a sweep.
      - [~] step 4: IN PROGRESS. Urgency. Sequence revised — see plan below.
            DONE: confusion-direction readout added to evals/run_evals.py
            (readout only; scoring.py and agent.py untouched, so the baseline is
            NOT void). Prints expected vs actual per field, only where the agent
            missed on >=1 run; tallies values in first-seen order with counts so
            a flip shows its split; reuses the scorer's `_matches` so list-valued
            ambiguous expectations can't be displayed as wrong when the gate
            counted them as a pass (cross-checked against score_case on a
            list-valued case across three value combinations); None prints as
            NO-DECISION; cases that pass the gate still appear if any run missed,
            with a gate column for context. Verified offline; pytest 2 passed.
            check_voting.py (a throwaway validation script, never tracked, no longer on
            disk) had its fakes updated to carry expected_* keys (test-fixture
            gap, not a product one).
            RESOLVED 2026-07-30: the stray Cyrillic fragment reported in Claude
            Code's prose never reached disk. Audited run_evals.py (only non-ASCII
            is one em dash in the module docstring, line 7) and all tracked files
            via git ls-files. Zero hits repo-wide. Fragment deliberately NOT
            quoted here so the repo stays ASCII-clean and the check greps clean.
            NEXT: blind label audit (see plan step 4).
- [ ] Repo 2 (mcp-knowledge-server): M5–M7, starts after M4. Scope it SMALLER
      than Repo 1 deliberately; it is a separate multi-day build.

## Progress estimate (as of session end 2026-08-03)
Repo 1 roughly 70-75% done (rough estimate, not measured; same basis as the
55-60% recorded 2026-07-30). Step 4 CLOSED BY DECISION, so urgency remains
UNMEASURED against the new policy. Step 7's documentation half SHIPPED
2026-08-03: README, MIT license, and the measured cost/latency table are public.
Remaining: step 5 (trigger wording, 30-45 min), step 6 (label adjudications,
45-75 min), and step 7's engineering half — regression gate, GitHub Actions CI,
per-case error handling, 1.5-2 hrs. The CI reduced-sweep design decision is still
unmade and is the highest-risk item left. Most cuttable work is step 6;
documenting the two labels as open questions with reasoning reads BETTER to a
technical buyer than resolving them silently.

## M4 baseline — frozen reference
STATUS: TAKEN 2026-07-30. RAW OUTPUT NOT RETAINED — evals/baselines/ was never
created and the sweep's stdout was lost. The figures recorded in this section are
transcribed from that output and are the AUTHORITATIVE record of the baseline.
Re-running would produce a NEW baseline, not evidence for this one, so the gap is
documented rather than papered over. Any future sweep must write raw output to a
file before anything else is done with it.
VALIDITY: still valid. The confusion-direction readout added afterward is a
readout change; re-running would reproduce 8/17. Will be VOID if any label changes.
- Commit SHA: 9cecd2d (HEAD at sweep time; code landed in f633cd4, docs on top)
- Instrument config: temp=0, n=3, per-case voting, even ties fail, judge advisory
  on first non-None run
- Deterministic pass: 8/17. SAME EIGHT CASES that passed M3's second run, so
  M3's 8/17 was modal and 7/17 was the outlier. The score did not move; the TRUST
  in it did. That was the entire point of steps 1-2.
- PASSING (8): easy_001, easy_004, easy_006, amb_001, amb_004, adv_001, adv_004,
  oos_001
- FAILING (9): easy_002, easy_003, easy_005, amb_002, amb_003, adv_002, adv_003,
  adv_005, oos_002
- Missed escalations: 0 at majority level AND 0 false-negative flips across all
  51 runs. Defensible README headline, backed by 51 runs not 2.
- Over-escalations: 3 — easy_002, adv_003, adv_005 (identical set to M3)
- Urgency wrong on 8 of 17. Seven fail 0/3 (easy_002, easy_003, easy_005,
  amb_002, adv_002, adv_003, oos_002) plus adv_005 0/3 with flips. Consistently
  wrong at temp 0, not inconsistently guessing.
- Per-field flip rates at temp=0: category 2/17 (amb_004, oos_002), urgency 1/17
  (adv_005), needs_human 1/17 (oos_001), trigger_cited 1/17 (oos_001). Variance
  COLLAPSED from ~18% verdict flips but did not vanish — temperature was the
  dominant source, not the only one.
- oos_001: escalated on 1 of 3 runs, absorbed by the majority vote, logged as a
  false-POSITIVE flip. WARNING did not fire (watches FN only) — resolved by the
  NOTE decision.
- No-decision (None) runs: 0 of 51. The safety stop never fired once.
- Judge: 2.7/5, 17/17 judged. amb_004 scored 1 (was 2) — finding HOLDS and is
  sharper: right answer, weakest reasoning in the suite, passes the gate. Best
  argument in the repo for an advisory judge. easy_006 scored 3 (was 2) — that
  half of the M3 claim WAS instrument noise and is RETRACTED. One case, not two.
  oos_002 (prompt injection) scored 5.
- REAL cost: 106,483 in / 20,725 out over 51 runs, 574.5s (9.6 min), 11.3s per
  run. Input-token projection was accurate; the 13-min estimate extrapolated from
  a single-case smoke test was ~35% HIGH — one case is a poor pace basis. USE
  THESE NUMBERS in the step-7 cost table, never a projection.

## M4 step 4 — the label-integrity finding (READ THIS BEFORE WRITING A RUBRIC)
The original diagnosis was "SYSTEM_PROMPT defines escalation in detail but gives
no low/medium/high rubric." That is still true but is NOT the whole story.

Reading the label_rationale fields of the seven urgency failures: SIX never argue
urgency at all. They justify escalation (or escalation + category) and appear to
have taken an urgency value as a default while the author was thinking about
needs_human:
  easy_002  low     — rationale argues escalation only ("no trigger fires")
  easy_003  medium  — escalation only ("money lost, regardless of amount")
  easy_005  medium  — escalation only (revenue trigger)
  amb_002   medium  — escalation only ("money lost, so escalation is strict True")
  adv_003   medium  — escalation + category, not urgency
  oos_002   medium  — escalation only (security concern)
By contrast the cases that PASS urgency 3/3 were reasoned about explicitly:
  easy_004  "Medium rather than high because it is one feature, not total loss."
  amb_003   "Urgency is strictly high: enterprise customer, widespread access loss."
  oos_001   "low urgency rather than forcing it into a support category."
IMPLICATION: writing a rubric to make the agent match those six could be fitting
the prompt to weak labels. Audit the labels first, blind.

adv_002 IS THE EXCEPTION THAT MATTERS: its rationale DOES argue urgency ("furious
tone, cosmetic issue... tests whether anger inflates urgency") and it still fails
0/3. That is a genuine agent defect on a purpose-built case.

UNCONFIRMED HYPOTHESIS (inference, not measurement): the agent may couple urgency
to escalation — escalate, therefore high. Supporting pattern: four failures share
expected_needs_human=true with expected_urgency=medium (easy_003, easy_005,
amb_002, oos_002), and all four `high` labels pass 3/3 (amb_003, amb_004,
adv_001, adv_004), which would pass for free under that coupling. The
confusion-direction readout now exists precisely to confirm or kill this. The fix
differs entirely by answer: coupling means the rubric must DECOUPLE urgency from
needs_human; tone-driven (adv_002's signature) means the rubric must say tone does
not set urgency. Different sentences, measured separately.

## M4 plan — reliability BEFORE prompt work
1. DONE. Temperature as a caller parameter (Option B).
2. DONE. --n majority voting, per-case.
3. DONE 2026-07-30. Baseline 8/17.
ORDER SWAPPED after reading the baseline table: URGENCY GOES FIRST, because every
case the trigger fix touches ALSO fails urgency, so the trigger fix alone converts
ZERO cases and a correct fix would look like a no-op at case level.
4. (was 5) IN PROGRESS. Urgency. Revised sub-sequence:
   a. [x] Confusion-direction readout (done, readout only, baseline valid)
   b. [!] BLIND AUDIT CONTAMINATED 2026-07-30. A text-only extract command was
          delegated to Claude Code, which read labels, label_rationale, AND
          baseline agent behavior, then adjudicated all six FROM agent behavior
          ("the agent rates urgency above low... the label is wrong"). Ronan read
          the output, so case-by-case blindness is unrecoverable on these six.
          DISCARDED: its label-problem vs agent-problem split, which was sorted
          by whether the agent's answer looked defensible.
          KEPT (text-level, agent-independent): easy_005 has an explicit "before
          Monday" deadline; easy_002 is a recovery-address change to a new
          domain; oos_002 is an active injection attempt.
          LESSON: blindness is an ACCESS property, not an instruction. Do not ask
          a tool with repo-wide read access to not look. Extract the field subset
          to a temp file first, then audit from that.
          REVISED PROCEDURE (policy-first, replaces case-by-case):
            i.   Write the urgency rubric at PRINCIPLE level, citing no case.
                 Anchor: how fast does this get worse if nobody touches it.
                 Hours=high, days=medium, no time pressure=low. Commit before
                 touching the dataset.
            ii.  Apply it mechanically to ALL 17 cases. Auditing only the six
                 would make the audit SAMPLE agent-determined, independent of
                 the contamination.
            iii. Out-of-dataset test is mandatory, not optional: the rubric must
                 classify tickets not in the suite or it is transcription.
          RESIDUAL RISK, recorded not cleaned: the rubric is written by someone
          who has seen the contaminated framing.
          STATUS 2026-07-31: sub-steps i, ii, iii DONE. Rubric written at
          principle level and committed as docs/urgency-policy.md before the
          dataset was touched; applied mechanically to ALL 17 cases, not the six
          agent-selected ones; validated 6/6 on out-of-suite tickets (policy §5).
          Worksheet v2 filled for all 17, validator clean. Artifacts committed to
          docs/audits/ (v1 and v2 worksheets, key.json).
          NOT DONE: the WHY review and THE DIFF against key.json. 4b's deliverable
          was always the diff, so this is CLOSED BY DECISION, not completed.
          FORM FINDING (v1 -> v2): v1 asked for BAND first and let severity,
          revenue and tone in; 6 of 17 bands contradicted their own DISTANCE and
          9 of 17 used one clock as a catch-all. v2 removed BAND and derived it.
          Same person, same policy, same tickets: every severity and revenue
          argument disappeared. The elicitation form was the instrument.
          RUBRIC USABILITY FINDING: the policy failed to hold the time frame in
          place for its own author, working from the document, one screen away.
          That predicts the agent's single pass at 4e. Both findings -> README.
   c. [x] CLOSED 2026-07-31. No label was compared or changed, so the 8/17
          baseline STANDS and remains valid. Recorded precisely: the baseline
          holds because nothing was changed, NOT because the audit found the
          labels correct. The diff was never run; that measurement is absent, not
          clean. Same rule as an unknown --case ID exiting 2 rather than 0/0.
   STEP 4 CLOSED 2026-07-31 BY DECISION, not completion. Demo repo; enough time
   spent on urgency. Sub-steps d, e, f NOT DONE and not scheduled. Consequence:
   no label and no prompt changed, so 8/17 stands and urgency behavior is
   UNMEASURED against the new policy. The pre-registered +4 prediction was never
   tested — say so, do not quietly drop it. Next work is step 7.
   d. [~] NOT DONE. Targeted diagnostic runs to confirm/kill the coupling hypothesis:
          `--case easy_003 --n 3`, same for easy_005, amb_002, oos_002, plus
          adv_002 for the tone hypothesis. ~15 agent calls, not a full sweep.
   e. [~] NOT DONE. Write the rubric, targeted at the mechanism actually confirmed.
   f. [~] NOT DONE. Full sweep, measure delta.
   PRE-REGISTERED PREDICTION (recorded before the label finding, DO NOT REVISE):
   +4 cases -> 12/17, from easy_003, amb_002, adv_002, oos_002 — the four failing
   ONLY on urgency. ANNOTATION: this assumed urgency was purely a prompt gap. The
   label-integrity finding puts that premise in question, so the prediction is
   likely wrong. Leaving it as recorded — a prediction that misses because its
   PREMISE was wrong is a finding about the premise, which is the entire reason
   for writing predictions down first.
5. (was 4) Fix the fifth trigger's wording so direction beats vocabulary. Re-run.
   PRE-REGISTERED PREDICTION: adv_005 esc goes 0/3 -> 3/3. Case-level movement
   depends on whether step 4 fixed its urgency. READ THIS DELTA AT FIELD LEVEL.
   easy_002 and adv_003 fire on different triggers, unaffected, remain for step 6.
6. Adjudicate two labels:
   - easy_002 (email address change): agent over-escalates, plausibly reading it
     as an account-takeover vector. Defensible — the label may be wrong, not the
     agent. If accepted, the security trigger must extend to credential-change
     requests so label and policy agree.
   - easy_005: baseline shows category 0/3 AND urgency 0/3 but escalation 3/3.
     Rewritten recently, so a rewrite error is as likely as an agent error.
   NOTE: easy_002 and easy_005 also appear in the step 4b audit list. Do not
   adjudicate the same label twice on different grounds — if 4b resolves them,
   step 6 shrinks accordingly.
7. PARTLY SHIPPED 2026-08-03. DONE and pushed: README.md (design decisions, the
   three eval findings, the frozen baseline with the measured cost/latency table,
   known gaps), MIT LICENSE, requirements.txt re-encoded to UTF-8 (pip freeze
   under PowerShell wrote UTF-16LE; pip decodes that correctly, so nothing was
   broken — UTF-8 is the portable default), load_dotenv() in the judge (it built
   a client without loading the environment itself, working only because every
   current path imports the agent first), schemas.py whitespace tidy.
   STILL OPEN: regression gate (pass band or majority-vote threshold, NOT a
   single-run hard threshold — it would flake), GitHub Actions CI (needs a
   REDUCED sweep mode; full 51-run sweep per push is untenable — design decision
   unmade), per-case error handling in the harness (a sweep that dies mid-run
   currently loses everything; already happened once).
RULE: each prompt change measured as a deliberate before/after, never batched.
RULE: write the PREDICTION down BEFORE running. Recorded afterward it is
rationalization, not measurement.
RULE: a label change is never a one-file change — label and SYSTEM_PROMPT must agree.
RULE: the instrument is FROZEN as of the baseline. Distinguish INSTRUMENT from
READOUT. Instrument = anything that produces or transforms a number: scoring,
voting, gate thresholds, temperature, n, AND THE LABELS. Change any of those and
the old baseline is VOID and must be re-taken. Readout = how existing numbers are
DISPLAYED: warning lines, formatting, added labels, confusion-direction output.
Additive readout changes do not void a baseline, because no recorded value moves.
Test: would re-running the old sweep under the new code produce a different
NUMBER? If yes, void. If it only prints differently, keep.

## Open threads / future case ideas
- Under-gathering evidence (spotted in the M1c demo): on cust_002's
  duplicate-charge ticket the agent called get_customer_history but skipped
  check_known_outages, even though billing_portal has an active outage. Candidate
  ambiguous case — does partial investigation still reach the right triage?
  adv_003 partly covers outage consultation; this would test the omission directly.
- easy_006 verifies the agent reads the revenue trigger NARROWLY (cancellation is
  revenue-contracting, so the trigger must not fire). Do not "fix" this case.
- Doc/tool divergence is a THIRD surface of the duplication problem, alongside
  JSON enum vs Pydantic Literal and policy doc vs SYSTEM_PROMPT. Tooling
  introduced an `unresolved` clock kind the policy never defined, and it landed
  on 4 of 17 entries before anyone noticed. Section 7 of the policy anticipated
  the category and missed this direction. FIXED 2026-07-31: the policy defines
  unresolved, the script assigns no band for it.
- Worksheet validator gap: WHAT is checked for PRESENCE but not for containing a
  date, so "bank dispute window" passes without "60 days". 5 of 17 name a problem
  instead of a closing date. Not worth a pass on its own; fix only if the audit
  is ever redone.
- Harness has NO per-case error handling: a sweep that dies mid-run loses
  everything, which has already happened once. Scheduled for step 7. Claude Code
  reported this as previously declined twice; no record of that decision exists
  here, so treat it as OPEN and decided in step 7, not inherited.
- Verify FIND/REPLACE results against disk, whoever authored the edit. A
  multi-item edit proposed in chat was applied differently than its author
  modeled, silently dropping missed-question #4 and orphaning the pointer to it
  at line 165. Claude Code caught it from the file; the chat-side author denied
  it from memory and nearly blocked the correct fix. The unreliable surface is
  any claim about file state not read from the file, including a chat session's.
- Claude Code reliability note: its CODE has been correct every time; its PROSE
  SUMMARIES have twice misdescribed what the code does (judge selection) or
  asserted prior decisions with no record (error handling declined twice). Verify
  claims about state against disk. Also watch for stray non-ASCII in its output.
- README design-decisions section (step 7), in Ronan's own words:
  agent-vs-workflow, the duplication tripwire, strict needs_human with split
  FN/FP reporting, acceptable-sets-fixed-at-authoring, judge-as-advisory, the
  temperature/variance finding, temperature-as-caller-parameter (instrument vs
  product), per-case-not-per-field voting, and the label-integrity finding
  (evals found bugs in the LABELS, not just the prompt — that is a strong and
  unusual thing to be able to say). This section is what contract buyers read.
- README headline claim, well supported: 0 missed escalations across 51 runs at
  temperature 0, with false negatives reported separately from false positives.
- README non-goals: blunt keyword matching on trigger citation; the judge being
  uncalibrated rather than a quality score.
- AUDIT A PUBLISHED ARTIFACT AGAINST ITS SOURCE BEFORE IT GOES PUBLIC. The README
  draft carried a per-run latency range (8.9-11.9s) presented as sweep data. The
  real observation was latency variance on repeated identical input, recorded in a
  section that has since moved out of the repo, so no surviving source supported
  the number as written. Also caught pre-publish: "four cases flipping a single
  field each" was wrong because oos_001 flipped two, and the flips table omitted
  trigger_cited, which broke the arithmetic between the two claims. All three were
  in the document whose thesis is measured-not-projected. A drafted claim inherits
  no authority from the care taken elsewhere in the same file.
- TRIGGER_CITED IS NEAR-UNFAILABLE AND IT IS INSIDE THE GATE (found 2026-08-04,
  NOT FIXED BY DECISION). scoring.py line 58 sets trigger_cited unconditionally
  True on non-escalating runs; on escalating runs it fails only when the
  reasoning contains NONE of 26 substrings, several as common as history,
  repeat, money, dispute. Demonstrated: reasoning that NEGATES a trigger still
  scores as citing it, and `fee` matches inside `coffee` (substring, no word
  boundary). The pointed case is adv_005-shaped text — "reduce seat count at
  renewal" — where reasoning that correctly RULES OUT the revenue trigger is
  credited for citing it. The check detects SILENCE, not error.
  It is the fourth condition in deterministic_pass (run_evals.py 69-71), so
  this is gate behavior, not a diagnostic wrinkle. CONSEQUENCE: 8/17 is
  OPTIMISTIC with respect to a stricter check — tightening can only fail cases
  that currently pass. The headline claim is unaffected; it rests on
  needs_human, which is scored strictly.
  NOT FIXED because TRIGGER_KEYWORDS and the match logic are INSTRUMENT: any
  change voids 8/17 and requires a re-sweep plus a new pre-registered
  prediction. Priced like a label change and declined on demo scope.
  README non-goal must be SHARPENED: the current wording ("does not check
  whether the trigger applies") is true but understates it. The accurate
  statement is that the check is unconditional in one direction and
  near-unfailable in the other, so it contributes less to the gate than being
  one of four all() conditions implies.
  ALSO: step 5's "direction beats vocabulary" is a SCORER problem as well as a
  prompt one. Fixing SYSTEM_PROMPT alone would produce no detectable movement
  in trigger_cited. Step 5's escalation prediction is unaffected.
- FLIP-RATE REFINEMENT (2026-08-04): the baseline's per-field flips list
  needs_human 1/17 (oos_001) and trigger_cited 1/17 (oos_001) as if
  independent. They are not. trigger_cited is unconditionally True on
  non-escalating runs, so it can only vary where escalation varies —
  oos_001's trigger_cited flip is DOWNSTREAM of its needs_human flip. The
  accurate statement is one flip with a dependent second, not two. Recorded
  numbers unchanged; the INTERPRETATION narrows. Extends the pre-publish
  catch already logged in this section.
- DATASET PATH IS CWD-RELATIVE (found 2026-08-04, fix specified, NOT YET
  APPLIED). run_evals.py line 39 is Path("evals/dataset/tickets.json") while
  line 30 goes out of its way to resolve the repo root from __file__. Run the
  harness from any other directory and it dies with FileNotFoundError, exit 1,
  before any API call — verified. pytest is unaffected because it derives
  rootdir from the test file's location. GitHub Actions works only by luck:
  actions/checkout leaves cwd at the workspace root. Would break under a
  working-directory key, a matrix that cds, or a composite action.
  FIX: DATASET = Path(__file__).resolve().parent / "dataset" / "tickets.json"
  Resolves to the same file from the repo root, so no recorded number moves and
  8/17 holds.
  PROCESS NOTE: this fix was agreed in chat and then not issued to any tool.
  Caught by a pre-flight `git status` showing a clean tree. Same family as
  "recorded DONE but never committed," arriving from a new direction — agreed
  in conversation, never applied. Keep the pre-flight check.
- TEST SUITE COVERS SCHEMA DRIFT ONLY (as of 2026-08-04). The two collected
  tests both live in tests/test_schema_sync.py and check enum/Literal
  agreement. Nothing exercised the agent loop, the scorer, the voting logic, or
  the confusion-direction readout; those were verified by paid sweeps, or by
  check_voting.py, which was a throwaway and no longer exists. The voting rules
  defended most carefully in this file — even ties fail, None distinct from
  False — had no automated protection. _majority, _aggregate, _matches, _wrong,
  _tally and _fmt are all pure functions and testable at zero token cost;
  tests/test_scoring.py addresses this.