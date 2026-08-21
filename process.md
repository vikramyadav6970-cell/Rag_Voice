# process.md — Running Status Log

Update this file at the END of every work session, before you stop. Any agent (or teammate)
picking up the project reads this file second, right after `context.md`, to know what's done
and what to do next. Don't let this go stale — a wrong "next step" wastes more time than a
missing one.

Keep entries short. Newest at the top.

---

## STATUS SNAPSHOT (always keep this section current — overwrite, don't append)

- **Current phase**: Phase 0 — Setup
- **Blocking issue**: none
- **Next immediate task**: Task 0.1 — repo scaffolding + API key acquisition
- **Dataset subset in use**: not yet decided
- **Deployed?**: no

---

## LOG (append new entries at the top, most recent first)

### 2026-08-22 — Agent (Task 0.0)
- What was done: Resolved latency target ambiguity and documented interpretation.
- Files changed: [README.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/README.md), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md)
- Decisions made: Retrieval pipeline (embed query → vector search → chunk assembly) is strictly targeted for P50/P70/P100 < 200ms; Generation latency (LLM TTFT & full completion) is tracked and benchmarked as a separate metric with detailed per-stage telemetry.
- Next task: Task 0.1 — repo scaffolding + API key acquisition.


<!--
Template for future entries:

### <date/time> — <who/which agent>
- What was done:
- Files changed:
- What was verified/tested:
- What's broken or unverified:
- Decisions made (and why — mirror any tech-stack changes into context.md too):
- Next task:
-->

---

## DECISIONS LOG (durable — don't delete old entries, this is a history)

- Chose Sarvam over ElevenLabs for STT — see context.md for reasoning.
- Chose Qdrant over FAISS/Pinecone for vector DB — see context.md for reasoning.
- <add further decisions here as they're made, with a one-line reason each>

## KNOWN ISSUES / RISKS

- Full 200ms latency budget may not be achievable if it's meant to include LLM generation —
  needs early confirmation (see PROMPTS.md Task 0.0). If unconfirmed, we're building against the
  "retrieval-through-context-assembly under 200ms, generation reported separately" interpretation.
- 55GB dataset will not be fully indexed given the time budget — using a documented subset.
