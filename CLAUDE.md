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
  in tests/ (to be written in M1c when tool definitions move into src/triage/)
- Model: claude-sonnet-4-6

## Curriculum state
- [x] M0: Scaffold — venv, .env hygiene, smoke test w/ forced tool use
- [x] M0b: GitHub remote connected, repo public and verified (no .env)
- [x] M1a: schemas.py — Pydantic models, Literal validation confirmed via REPL
- [x] M1b: tools.py — FAKE_CUSTOMERS/FAKE_OUTAGES stubs, structured not-found errors
- [ ] M1c: agent.py — the loop. NEXT UP. Concepts: stop_reason, tool-result
      feedback, growing message list, natural vs safety termination
- [ ] M1d: schema sync test (tests/) + intro to pytest
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
- Pending in M1c: stop_reason values, tool_result blocks, max-turns safety cap

## Python covered (reference only, don't re-teach)
imports/venv/pip -m; lists vs dicts (index vs key); def/return/if-in pattern;
__init__.py = package marker; module vs script; reading tracebacks
(syntax vs name vs import vs API 400); editor→save→REPL verify rhythm

## Open threads
- M1b explain-back: partially done (gist right, details corrected). Reinforce
  function mechanics via scenario questions rather than re-drilling.
- Duplication stance: RESOLVED — option (c), cheap sync test as tripwire.
  Goes in README design-decisions section in M4.