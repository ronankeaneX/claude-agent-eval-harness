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

## Tech decisions (settled — do not relitigate)
- Python for everything (single toolchain; TS port is future work)
- Structured output via tool use; agent uses tool_choice "auto", smoke test used forced tool
- Agent (Option B) over workflow (Option A): repo exists to showcase agentic skill
- Pydantic for Python-side validation; Literal mirrors the API enum
- Schema duplication (JSON enum vs Literal): accepted, protected by a sync test
  in tests/ — tool definitions now live in src/triage/agent.py as
  TOOL_DEFINITIONS (module level, importable by tests); test itself is M1d
- Model: claude-sonnet-4-6

## Curriculum state
- [x] M0: Scaffold — venv, .env hygiene, smoke test w/ forced tool use
- [x] M0b: GitHub remote connected, repo public and verified (no .env)
- [x] M1a: schemas.py — Pydantic models, Literal validation confirmed via REPL
- [x] M1b: tools.py — FAKE_CUSTOMERS/FAKE_OUTAGES stubs, structured not-found errors
- [x] M1c: agent.py — the loop. Verified end-to-end Jul 28 via
      scripts/run_agent_demo.py: agent chose get_customer_history, consumed the
      tool_result, then hit the natural stop (record_triage), not MAX_TURNS.
- [ ] M1d: schema sync test (tests/) + intro to pytest. NEXT UP.
- [ ] M2: Golden dataset (easy/ambiguous/adversarial/out-of-scope taxonomy)
- [ ] M3: Scoring — deterministic checks + LLM-as-judge
- [ ] M4: Regression gate, GitHub Actions CI, cost/latency table, README, MIT license
- [ ] Repo 2 (mcp-knowledge-server): M5–M7, starts after M4
- [ ] Final 2 days before exam: pure exam review, all five domains, missed questions re-run

## Exam concepts covered so far (CCA-F mapping)
- D1 Agentic Architecture: workflow vs agent = WHO decides the next step;
  forced vs auto tool_choice; agent = loop + tools + termination
- D4 Tool Design: JSON Schema basics; structured errors from tools
  (return error dicts, don't crash); tools-as-forms trick for structured output
- D1 Agentic Architecture (the loop, from M1c): stop_reason is the branch point —
  "tool_use" = keep looping, "end_turn" = Claude stopped without deciding,
  "max_tokens"/other = treat the reply as unreliable. Two terminations, and they
  are NOT the same thing: the NATURAL stop is a finish-line tool (record_triage
  called → return), the SAFETY stop is the MAX_TURNS cap on the for-loop.
  Reaching the safety stop is a failure signal, not a normal exit.
- D4 Tool Design (from M1c): the tool_result block must quote back Claude's
  tool_use id, and BOTH sides get appended each round (assistant's request, then
  our results as a user message) — that growing message list IS the agent's
  memory of its own investigation. Validate tool input through Pydantic on the
  way out; the model's JSON is untrusted until it is parsed.

## Python covered (reference only, don't re-teach)
imports/venv/pip -m; lists vs dicts (index vs key); def/return/if-in pattern;
__init__.py = package marker; module vs script; reading tracebacks
(syntax vs name vs import vs API 400); editor→save→REPL verify rhythm

## Open threads
- M1b explain-back: partially done (gist right, details corrected). Reinforce
  function mechanics via scenario questions rather than re-drilling.
- Duplication stance: RESOLVED — option (c), cheap sync test as tripwire.
  Goes in README design-decisions section in M4.
- M2 test-case candidate (spotted in the M1c demo): on cust_002's duplicate-charge
  ticket the agent called get_customer_history but skipped check_known_outages,
  even though billing_portal has an active outage in FAKE_OUTAGES. Under-gathering
  evidence once it feels confident is exactly an "ambiguous" bucket case — does
  partial investigation still reach the right triage?
- M1c explain-back + scenario quiz: NOT yet done. Code was verified by running it,
  but Ronan owes the design explain-back and 2-3 CCA-F questions per the working
  agreement. Do this before starting M1d.