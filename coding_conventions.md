# coding_conventions.md — Rules for Anyone (Human or AI) Writing Code Here

These are hard rules, not suggestions. If a prompt or instruction conflicts with this file,
this file wins. Read `context.md` for project background before writing any code.

## General

1. **Don't reinvent libraries.** If a well-maintained package does it (chunking, vector DB
   client, HTTP retries, audio handling), use it. Do not hand-roll an HNSW index, a retry
   decorator, or an HTTP client when `qdrant-client`, `tenacity`, and `httpx` already exist.
2. **No unnecessary code.** No speculative abstraction, no config options nobody asked for,
   no "just in case" flexibility. Build what the current task needs.
3. **Production-grade only.** No notebook-style throwaway scripts committed to the main
   codebase. Every file that goes into `src/` should have error handling, type hints
   (Python) or types (TypeScript), and be something you'd be fine deploying as-is.
   Exploratory/scratch work belongs in a `notebooks/` or `experiments/` folder, clearly
   separated, and is never imported by production code.
4. **No dead code.** If you replace an approach, delete the old one — don't comment it out
   "just in case." `process.md`'s decisions log is where history lives, not commented code.
5. **Every external call gets a timeout and a retry policy.** STT calls, vector DB queries,
   LLM generation calls — all of them. Latency-critical code (retrieval, chunking) must be
   wrapped with timing instrumentation from day one, not bolted on later.
6. **Secrets never get committed.** All API keys via `.env` (gitignored), with an
   `.env.example` checked in showing the required variable names with no values.
7. **Every task ends with an update to `process.md`.** Not optional. If you did work and
   didn't log it, the work effectively didn't happen for the next agent.

## Python (backend)

- FastAPI for the service layer. Pydantic models for every request/response — no raw dicts
  crossing a route boundary.
- Async I/O for anything that hits a network (STT, vector DB, LLM API) — don't block the
  event loop.
- One module per pipeline stage (`stt.py`, `chunking.py`, `retrieval.py`, `generation.py`,
  `guardrails.py`, `harness.py`) — no god-files.
- Type hints required on every function signature.

## React (frontend)

- Functional components + hooks only. No class components.
- One component per file. Co-locate a component's styles/tests with it.
- All API calls go through a single `api/` client module — no `fetch()` scattered through
  components.
- Loading, error, and guardrail-refusal states must all be explicitly designed — no silent
  failures, no infinite spinners.

## Naming / structure

- `snake_case` for Python, `camelCase` for TypeScript/JS, `PascalCase` for React components.
- Env vars: `SCREAMING_SNAKE_CASE`, prefixed by service (`SARVAM_API_KEY`, `QDRANT_URL`,
  `GENERATION_API_KEY`).

## Commits

- One logical change per commit. Message format: `<phase>: <what changed>` e.g.
  `phase1: add semantic chunking strategy`.

## Before marking any task "done"

- Does it have a timeout/retry if it calls a network service?
- Is it timed/instrumented if it's on the latency-critical path?
- Did you update `process.md`?
- Did you update `context.md` if a tech-stack decision changed?
