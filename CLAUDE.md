# CLAUDE.md — claude-agent-eval-harness

## What this project is
Support-ticket triage AGENT (not workflow) + evaluation harness.
Portfolio repo for Ronan Keane (applied AI / contract positioning) AND
hands-on prep for the CCA-F exam. Exam date: ~Aug 4, 2026 (postponed from Jul 29).

## Working agreement (instructor mode, revised Jul 27)
- Exam prep and repo build have EQUAL priority. Both purposes served at every milestone.
- Claude provides complete annotated code, or Claude Code generates it.
  Ronan does NOT hand-type code — that rule is retired.
- Every milestone: concept brief FIRST (mapped to exam domain) → code as the
  working example → scenario quiz in CCA-F format (2-3 questions).
- Quizzes are delivered as MULTIPLE CHOICE with distractors, matching exam format.
  Free-recall phrasing tests a different skill than the exam does.
- Ronan's deliverables per milestone: explain back the DESIGN (not syntax),
  answer scenario questions, make one design decision with reasoning.
- Python syntax explained only when Ronan asks. No unprompted syntax lessons.
- Never touch .env or .gitignore. Never commit secrets.
- Flag open items neutrally. No pressure language about outstanding deliverables.

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
  recorded as DIAGNOSTICS only (they are what pointed at the missing urgency
  rubric in M3).
- Even ties FAIL. No majority means no verdict to gate on. Never fires at the
  n=3 default; cheap insurance for anyone running --n 4.
- None results (safety stop or failure to decide) count as FAILED runs for
  voting, and are a DISTINCT value in flip detection — never folded into False.
  "Never decided" is a loop/safety-stop defect; "decided no" is a judgment
  defect. Collapsing them makes a MAX_TURNS bug read as an escalation bug.
- Baseline is recorded under the FINAL instrument configuration (temperature=0,
  n=3, per-case voting). NOT temp=0 single-run — otherwise every later delta
  compares numbers measured with different instruments. Build the instrument,
  freeze it, then measure everything with it.
- needs_human scored STRICTLY, always. False negatives (missed escalations)
  reported SEPARATELY from false positives — never blended into one number.
  This extends to the voting layer: a case that fails to escalate on even 1 of n
  runs is a probabilistic missed escalation in production and must appear in the
  false-negative diagnostics even when it passes the gate on majority. The
  harness prints an explicit WARNING when a majority pass conceals a real miss —
  majority voting exists to absorb intermittent failure, and escalation is the
  one field where absorbing it is exactly wrong.
- Acceptable-value LISTS allowed on category/urgency for explicitly ambiguous
  cases only (3 of 17). Sets fixed at authoring time, NEVER widened to make a
  run pass. Disagreement means either the agent is wrong or the label is wrong.
- No vote-shopping: never rerun a failed case and report the best run, and never
  raise n until a case passes. Both are the runtime equivalent of widening
  acceptable-value sets after the fact — adjusting the measurement standard to
  fit the observed result.
- Every dataset case carries a label_rationale.
- Fifth escalation trigger added: revenue-expanding requests. adv_005 is its
  matched negative test (seat REDUCTION must not fire it).
- M3 Option A: deterministic field checks GATE the build; the LLM judge is
  advisory — reported prominently but never fails a build. Judges are models and
  therefore noisy; a gate nobody trusts is worse than no gate.
- Judge runs ONCE per case even under n-run voting, scoring the first NON-NONE
  run's output and recording which run index was judged; skipped only when ALL n
  runs are None. Tripling calls on an uncalibrated advisory signal buys nothing.
- Trigger-citation check promoted from judge to deterministic (five triggers are
  known strings, no model call needed). Blunt keyword match — acknowledge as a
  limitation in the README non-goals section.
- Unknown --case ID exits 2 rather than reporting 0/0. An instrument must not
  report a clean result for a measurement it never took.

## Curriculum state
- [x] M0: Scaffold — venv, .env hygiene, smoke test w/ forced tool use
- [x] M0b: GitHub remote connected, repo public and verified (no .env)
- [x] M1a: schemas.py — Pydantic models, Literal validation confirmed via REPL
- [x] M1b: tools.py — FAKE_CUSTOMERS/FAKE_OUTAGES stubs, structured not-found errors
- [x] M1c: agent.py — the loop. Verified end-to-end: agent chose
      get_customer_history, consumed the tool_result, hit the natural stop
      (record_triage), not MAX_TURNS. TriageRun metrics + --n variance flag added.
      Explain-back and 3/3 scenario quiz completed.
- [x] M1d: tests/test_schema_sync.py — drift tripwire, verified RED then GREEN.
      pytest introduced. Quiz 1/2 (missed the silent-drift-direction question).
- [x] M2: evals/dataset/tickets.json — 17 cases (6 easy, 4 ambiguous,
      5 adversarial, 2 out-of-scope). Escalation split roughly 50/50 so an agent
      can't score well by always guessing the majority. All labels reviewed and
      endorsed by Ronan; easy_005 flipped to needs_human=true with the matching
      SYSTEM_PROMPT trigger added. Quiz 2/2.
- [x] M3: evals/scoring.py + evals/judges/reasoning_judge.py + evals/run_evals.py.
      Both tracks running. Findings below. Quiz 1/2 (missed the
      reproducibility-is-a-property-of-the-instrument question).
- [ ] M4: reliability first, THEN prompt work, THEN gate/CI/README. See plan below.
      - [x] step 1: DONE. Temperature parameterized as a caller argument
            (Option B). agent.py: threaded through BOTH run_triage and
            run_triage_with_metrics via sampling_kwargs built once outside the
            loop; no literal temperature in the agent by design.
            run_evals.py:47 and reasoning_judge.py:79 pin 0. Quiz 1.5/3.
            Only one messages.create in agent.py, so the every-call-site risk
            did not apply. Near-miss: parameter existed for one turn while
            neither caller passed it — a sweep then would have looked measured
            and sampled at 1.0.
            DELIBERATE: scripts/run_agent_demo.py stays at API default so its
            --n flag demonstrates the variance the harness controls for. Not an
            oversight; document it as a demo.
      - [x] step 2: DONE. --n majority voting (default 3), PER-CASE on
            deterministic_pass. Even ties FAIL: no majority means no verdict.
            None results count as failed runs and are a DISTINCT value in flip
            detection, not folded into False — "never decided" (loop/safety-stop
            defect) vs "decided no" (judgment defect) must not be collapsed.
            Diagnostics: per-field flip rates with offending case IDs +
            needs_human FN/FP split + an explicit WARNING when a majority pass
            conceals a real missed escalation. --case with unknown ID exits 2
            rather than reporting 0/0.
            Verified OFFLINE with synthetic scored dicts (no API calls):
            2-of-3 passes, 1-of-3 fails, even tie fails, urgency-only flip
            detected, intermittent miss shows false_negative=False /
            any_false_negative=True, None run flips all four fields.
            CLI: --help correct, --n 0 and --case nope_999 rejected. Quiz 3/3.
            VERIFIED ON DISK (run_evals.py:93-95, 119, 121): judge scores the
            first NON-NONE run via a `judged_result is None` first-wins guard;
            judged_index is 1-based and stored on the row at :113 regardless of
            --judge, so diagnostics always report which run was or would have
            been judged. Skipped only when every run returned None (:119).
            PROJECTED cost for a --n 3 sweep: ~51 runs, ~8 min, ~105k in /
            ~21k out, +17 calls with --judge. This is SCALED FROM the M3
            single-run sweep, not measured. Replace with real numbers after
            step 3.
      - [ ] step 3: ACTIVE. Re-baseline. See "M4 baseline — frozen reference".
- [ ] Repo 2 (mcp-knowledge-server): M5–M7, starts after M4
- [ ] Final 2 days before exam: pure exam review, all five domains, missed
      questions re-run (see "missed questions" list at the bottom)

## M3 findings — baseline BEFORE any fixes
- Deterministic pass: 7/17, then 8/17 on IDENTICAL conditions (the judge runs
  after triage and cannot affect it). ~18% of the suite flipped verdict between
  runs. NEITHER NUMBER IS THE REAL SCORE.
- ROOT CAUSE: the agent runs at the API default temperature (1.0). Fix is
  temperature=0 for eval runs plus n-run majority voting in the eval runner.
- REPRODUCIBLE across both runs (real defects, not variance):
  * 0 missed escalations both runs — the policy errs safe. README headline claim.
  * Over-escalations: easy_002, adv_003, adv_005 — identical set both runs.
  * adv_005 fails escalation EVERY run: the agent keyword-matches "seats"/"plan"
    against the revenue trigger instead of reading DIRECTION. easy_006
    (cancellation) passes, isolating the cause to seat/plan vocabulary.
    This is a bug in the trigger wording, found by a case added one turn earlier.
  * Urgency fails on 7 cases spread across every case type. SYSTEM_PROMPT
    defines escalation criteria in detail but gives NO low/medium/high rubric —
    the agent is guessing at a dimension that was never defined.
    General lesson: evals mostly find PROMPT bugs, not model bugs.
  * easy_005 category fail and amb_003 trigger_cited fail: both reproducible.
- Judge: 2.9/5 average, advisory, UNCALIBRATED — use as relative ranking between
  cases, not as an absolute quality measure. It caught amb_004 and easy_006
  passing deterministically while scoring 2 (right answer, weak reasoning), which
  is precisely the gap the judge exists to surface.
  CAVEAT (found at M4 step 1): the judge itself ran at temperature 1.0, so part
  of the 2.9/5 spread may be INSTRUMENT NOISE rather than output quality. A judge
  at 1.0 can score the same reasoning differently on re-run. The amb_004 /
  easy_006 finding needs re-verification now that the judge is pinned to 0 —
  that finding is load-bearing in the README argument for why an advisory judge
  earns its cost.
- Cost per full sweep: ~35k input / ~7k output tokens; 158s without judge,
  234s with judge (17 extra calls).
- One defect fixed during the run: evals/run_evals.py was missing the repo-root
  sys.path bootstrap that scripts/run_agent_demo.py already had.

## M4 plan — reliability BEFORE prompt work
1. DONE. Temperature as a caller parameter (Option B), not an agent constant.
   See curriculum state for details.
2. DONE. --n majority voting, per-case. See curriculum state for details.
3. ACTIVE. Re-baseline and RECORD under the FROZEN instrument config
   (temp=0 / n=3 / per-case / judge advisory on first non-None run).
   Prerequisites before spending the calls:
   - - judge scores the first NON-NONE run: VERIFIED ON DISK, no change needed.
     run_evals.py:93-95 first-wins guard, :119 skip-only-if-all-None,
     :113 judged_index stored regardless of --judge.
   - COMMIT first. The baseline must be attributable to a SHA or "we went from
     X to Y" is unfalsifiable.
   Command: python evals\run_evals.py --n 3 --judge
   Record into "M4 baseline — frozen reference" below. Include --judge: the M3
   judge finding was collected at temperature 1.0 and needs re-verification.
   Expect roughly 7-8/17. MATERIALLY HIGHER means the voting logic is being
   generous, not that the agent improved — no defect has been touched yet.
4. Fix the fifth trigger's wording so direction beats vocabulary. Re-run, measure delta.
5. Add an urgency rubric to SYSTEM_PROMPT. Re-run, measure delta.
6. Adjudicate two labels:
   - easy_002 (email address change): agent over-escalates, plausibly reading it
     as an account-takeover vector. Defensible — the label may be wrong, not the
     agent. If accepted, the security trigger must be extended to credential-change
     requests so label and policy agree.
   - easy_005: run `python evals/run_evals.py --case easy_005` and look at the
     actual output before deciding. This case was rewritten recently, so a
     rewrite error is as likely as an agent error.
7. Regression gate (pass band or majority-vote threshold, NOT a single-run hard
   threshold — it would flake), GitHub Actions CI, cost/latency table, README,
   MIT license.
RULE: each prompt change measured as a deliberate before/after, never batched.
RULE: a label change is never a one-file change — label and SYSTEM_PROMPT must agree.
RULE: the instrument is FROZEN as of the baseline. If the harness itself changes
later, the old baseline is void and must be re-taken — a delta measured across
two different instruments is not a delta.

## M4 baseline — frozen reference
STATUS: not yet taken. Run step 3.
- Commit SHA:
- Instrument config: temp=0, n=3, per-case voting, even ties fail, judge
  advisory on first non-None run
- Deterministic pass: __/17
- Per-case verdicts (for case-by-case diffing, not just the total):
- Missed escalations: majority-level count __ ; intermittent misses caught by
  the WARNING line __ (a majority pass concealing a real miss still counts)
- Per-field flip rates at temp=0 (category / urgency / needs_human /
  trigger_cited): residual variance is a FINDING, not noise to ignore
- No-decision (None) runs: __ of 51
- Judge average: __/5 ; do amb_004 and easy_006 still score ~2 now that the
  judge is pinned?
- REAL cost and wall-clock: __ in / __ out, __ s. Replaces the step-2
  projection (~51 runs, ~8 min, ~105k in / ~21k out) — that was scaled from the
  M3 single-run sweep, never measured. Do not carry a projection into the step-7
  cost table.

## Exam concepts covered (CCA-F mapping)
- D1 Agentic Architecture: workflow vs agent = WHO decides the next step (not
  linear vs branching — workflows can branch, loop, retry); forced vs auto
  tool_choice; agent = goal + tools + loop + termination.
- D1 stop_reason as the branch point: "tool_use" = keep looping, "end_turn" =
  Claude stopped without deciding, "max_tokens"/other = reply is unreliable.
  Two terminations and they are NOT the same: NATURAL stop is the finish-line
  tool (record_triage called → return), SAFETY stop is the MAX_TURNS cap.
  Reaching the safety stop is a failure signal, not a normal exit.
- D4 Tool Design: JSON Schema basics; structured errors from tools (return error
  dicts, don't crash — a raised exception kills the loop, a returned error
  informs it); tools-as-forms trick for structured output; the tool_result block
  must quote back Claude's tool_use id, and BOTH sides get appended each round
  (assistant's request, then results as a user message).
- Context Management: input tokens COMPOUND across loop turns (each round
  re-sends system prompt + all tool definitions + full history); output tokens
  don't. Verbose tool results are a tax paid on every subsequent turn.
  MAX_TURNS protects the bill as well as the logic.
- Evals: deterministic vs judge tracks — stable structured fields get exact-match
  checks, free-text fields get an LLM judge; push everything possible into the
  deterministic column. Golden dataset taxonomy (easy/ambiguous/adversarial/
  out-of-scope) and why an all-easy suite scores 96% and predicts nothing.
  Fixture consistency rule: each case must contain exactly the intended signals
  and no accidental ones, or you measure the model's response to an accident.
  Drift asymmetry: Pydantic WIDER than the JSON enum = silent misclassification;
  NARROWER = loud ValidationError. Judge failure modes: verbosity bias,
  self-preference, position bias. Tests (static, free, deterministic) vs evals
  (model judgment, costs calls, nondeterministic).
- Reproducibility: it is a property of the MEASURING INSTRUMENT, not of the
  system under test. Measure at temperature 0 so the harness can distinguish a
  real regression from run-to-run variance; production temperature is a separate
  product decision. Model latency is nondeterministic too (8.9–11.9s observed on
  identical input) — CI timeouts need margin, not an exact expectation.
- Residual variance: temperature=0 shrinks output variance but does NOT guarantee
  identical outputs. So temperature=0 and n-run voting are a PAIR, not
  alternatives: step 1 shrinks the noise, step 2 measures through what's left.
  Several stable runs are evidence of low variance, not proof of zero variance —
  and a gate that flakes once a month is the "gate nobody trusts" problem again.
- Voting unit (per-case vs per-field): per-field majorities can assemble a
  passing composite that no individual run produced, i.e. gating on a synthetic
  agent. Per-case is harsher on multi-field cases by pure arithmetic, which is
  the real tradeoff. Resolution: gate on the honest unit, instrument at the
  finer grain.
- Determinism vs correctness: determinism makes defects REPRODUCIBLE, it does not
  remove them. A deterministic agent citing the wrong trigger cites that same
  wrong trigger every run (adv_005 is the live proof in this repo), so
  temperature=0 never makes a correctness check redundant.
- Vote-shopping as an anti-pattern: rerunning until pass, reporting the best run,
  or raising n until a case passes are all the runtime form of moving the
  standard to fit the result. Same family as widening acceptable-value sets.
- Baseline discipline: a baseline inherits its authority entirely from the
  instrument that produced it. Freeze the instrument, then take the number.
  Change the harness later and the old baseline is VOID, not merely stale — a
  delta measured across two instruments is not a delta. And never batch two
  changes: +4 from two edits at once teaches almost nothing, since one could
  have contributed +5 and the other -1.
- Failure-mode granularity: an instrument must distinguish KINDS of failure, not
  just count them. None vs False in this repo (never decided vs decided no) is
  the worked example — collapsing them sends you to tune a prompt when the bug
  is in the loop. Same principle behind splitting FN from FP on escalation, and
  behind erroring on an unknown --case ID instead of reporting 0/0.

## Python covered (reference only, don't re-teach)
imports/venv/pip -m; lists vs dicts (index vs key); def/return/if-in pattern;
__init__.py = package marker; module vs script vs config file; reading tracebacks
(syntax vs name vs import vs API 400); cascading errors — only the FIRST one is
real; editor→save→REPL-verify rhythm; three terminal "rooms" (PowerShell / >>> /
Claude Code) and reading the prompt to know which one you're in;
conditional kwargs (build a dict, add the key only when set) for optional API
params that must be OMITTED rather than sent as None; **kwargs spread into a
call; thin wrappers must FORWARD new params or they become silent holes;
keyword args over positional at call sites, so a signature change can't rebind
silently; VS Code terminal recovery (Ctrl+`) and that a new terminal starts
without the venv active.

## Missed exam questions — re-run these during final review
1. Drift direction (M1d Q2): Pydantic Literal wider than the JSON enum produces
   SILENT misclassification, not a ValidationError. The model is constrained by
   the JSON enum and simply cannot emit the new value.
2. Temperature/reproducibility (M3 Q2): the answer is "reproducibility is a
   property of the instrument," NOT "lower production temperature too" — that
   changes the product to suit the test.
   STATUS: answered correctly at M4 step 1 Q2 in disguised form. Keep on the
   list anyway — the exam likes re-costuming this one.
3. Residual variance at temperature=0 (M4 step 1 Q1): the objection to trusting
   single runs is that OUTPUTS can still vary. Latency variance is a DIFFERENT
   answer, belonging to "CI timeouts need margin." Keep the two separate; a
   scenario question can bait a swap.

## Open threads / future case ideas
- Under-gathering evidence (spotted in the M1c demo): on cust_002's
  duplicate-charge ticket the agent called get_customer_history but skipped
  check_known_outages, even though billing_portal has an active outage. Candidate
  ambiguous case — does partial investigation still reach the right triage?
  Note adv_003 partly covers outage consultation; this would test the omission
  directly rather than the classification.
- easy_006 now serves a specific purpose: it is the only case verifying the agent
  reads the revenue trigger NARROWLY (cancellation is revenue-contracting, so the
  trigger must not fire). Its label_rationale says so — do not "fix" this case.
- README design-decisions section (M4 step 7) should carry, in Ronan's own words:
  agent-vs-workflow, the duplication tripwire, strict needs_human with split
  false-negative/false-positive reporting, acceptable-sets-fixed-at-authoring,
  judge-as-advisory, the temperature/variance finding, temperature-as-caller-
  parameter (instrument vs product), and per-case-not-per-field voting. This
  section is what contract buyers actually read.
- README non-goals should carry: blunt keyword matching on trigger citation, and
  the judge being uncalibrated rather than a quality score.