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
- needs_human scored STRICTLY, always. False negatives (missed escalations)
  reported SEPARATELY from false positives — never blended into one number.
- Acceptable-value LISTS allowed on category/urgency for explicitly ambiguous
  cases only (3 of 17). Sets fixed at authoring time, NEVER widened to make a
  run pass. Disagreement means either the agent is wrong or the label is wrong.
- Every dataset case carries a label_rationale.
- Fifth escalation trigger added: revenue-expanding requests. adv_005 is its
  matched negative test (seat REDUCTION must not fire it).
- M3 Option A: deterministic field checks GATE the build; the LLM judge is
  advisory — reported prominently but never fails a build. Judges are models and
  therefore noisy; a gate nobody trusts is worse than no gate.
- Trigger-citation check promoted from judge to deterministic (five triggers are
  known strings, no model call needed). Blunt keyword match — acknowledge as a
  limitation in the README non-goals section.

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
- Cost per full sweep: ~35k input / ~7k output tokens; 158s without judge,
  234s with judge (17 extra calls).
- One defect fixed during the run: evals/run_evals.py was missing the repo-root
  sys.path bootstrap that scripts/run_agent_demo.py already had.

## M4 plan — reliability BEFORE prompt work
1. temperature=0 on the agent (one line in client.messages.create)
2. n-run majority voting per case in evals/run_evals.py (commodity code —
   Claude Code's job; the --n flag on the demo script is the per-case precedent)
3. Re-baseline and RECORD the number. This is the "before" for everything after.
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

## Python covered (reference only, don't re-teach)
imports/venv/pip -m; lists vs dicts (index vs key); def/return/if-in pattern;
__init__.py = package marker; module vs script vs config file; reading tracebacks
(syntax vs name vs import vs API 400); cascading errors — only the FIRST one is
real; editor→save→REPL-verify rhythm; three terminal "rooms" (PowerShell / >>> /
Claude Code) and reading the prompt to know which one you're in.

## Missed exam questions — re-run these during final review
1. Drift direction (M1d Q2): Pydantic Literal wider than the JSON enum produces
   SILENT misclassification, not a ValidationError. The model is constrained by
   the JSON enum and simply cannot emit the new value.
2. Temperature/reproducibility (M3 Q2): the answer is "reproducibility is a
   property of the instrument," NOT "lower production temperature too" — that
   changes the product to suit the test.

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
  judge-as-advisory, and the temperature/variance finding. This section is what
  contract buyers actually read.