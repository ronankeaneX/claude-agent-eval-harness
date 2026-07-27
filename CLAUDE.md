# CLAUDE.md — claude-agent-eval-harness

## What this project is
Support-ticket triage AGENT (not workflow) + evaluation harness.
Portfolio repo for Ronan Keane (applied AI / contract positioning) AND
hands-on prep for the CCA-F exam (exam date: July 29, 2026).

## Working agreement (instructor mode)
- Ronan hand-writes judgment code: agent loop, judge prompts, scoring logic, schemas.
- Claude Code handles commodity code ONLY: scaffolding, CI YAML, README skeletons, plumbing.
- Explain-back rule: anything Claude Code writes, Ronan must be able to explain.
- Never touch .env or .gitignore. Never commit secrets.
- One design decision per milestone, made by Ronan with reasoning.

## Tech decisions (settled — do not relitigate)
- Python for everything (single toolchain; TS port is future work)
- Structured output via tool use; agent uses tool_choice "auto", smoke test used forced tool
- Agent (Option B) over workflow (Option A): repo exists to showcase agentic skill
- Pydantic for Python-side validation; Literal mirrors the API enum (accepted duplication)
- Model: claude-sonnet-4-6

## Curriculum state
- [x] M0: Scaffold — venv, .env hygiene, smoke test w/ forced tool use, pushed to GitHub
- [x] M1: The agent — M1a schemas.py (IN PROGRESS), M1b stub tools, M1c the loop, M1d termination
- [ ] M2: Golden dataset (easy/ambiguous/adversarial/out-of-scope taxonomy)
- [ ] M3: Scoring — deterministic checks + LLM-as-judge
- [ ] M4: Regression gate, GitHub Actions CI, cost/latency table, README, MIT license
- [ ] Repo 2 (mcp-knowledge-server): M5–M7, starts after M4 completes

## Lessons already covered (don't re-teach, do reinforce)
imports/venv/pip -m; lists vs dicts (index vs key); tool_choice forced vs auto;
workflow vs agent = WHO decides the next step; __init__.py = package marker;
reading tracebacks (syntax vs env vs API 400); JSON Schema basics

## Open threads
- Pending: Ronan's position on schema duplication (input_schema vs Literal)
- Day 6 reserved for exam review; missed exam-check questions to be re-run