# Build Playbook — Voice-Enabled RAG (HH Goa 2026, Task 2)

Deadline: **August 22, 2026, 11:59 PM** — this document assumes well under 24 hours of build
time. It's ordered so that dropping the last 1–2 tasks of any phase still leaves you with a
working, demoable, submittable system. Phases 1–3 and 6–7 are the non-negotiable spine; Phases
4–5 are what make the submission *good*, not just working — don't skip them, but they can be
done in parallel with frontend if you have more than one person.

**How to use this file**: each task below is a self-contained prompt. Paste it directly into
your AI coding agent (Claude Code, Antigravity, Cursor, etc.) in a fresh or ongoing session.
Every prompt tells the agent to read `context.md` and `coding_conventions.md` first and to
update `process.md` after — so agents stay in sync even across tool switches.

If you have multiple people: Phase 1 (backend/retrieval) and Phase 6 (frontend) can run in
parallel from the start, once Task 0.1–0.3 are done, since the frontend only needs the API
contract, not the finished backend.

---

## Phase 0 — Setup (do this first, ~30–45 min)

### Task 0.0 — Resolve the latency ambiguity (do this before writing any code)
The spec says "chunking + vector DB retrieval + everything through to final output" should be
under 200ms. Taken completely literally, that includes LLM generation, which is not realistic
with any external LLM API. Before committing engineering time:
- If there's a way to ask the organizers, ask whether 200ms covers generation or just
  retrieval-through-context-assembly.
- If you can't get an answer in time, build against this documented interpretation (already in
  `context.md`): **retrieval pipeline (embed query → vector search → chunk assembly) must hit
  P50/P70/P100 under 200ms; generation latency is measured and reported separately, clearly
  labeled.** This is defensible and still respects the spirit of the requirement — say so
  explicitly in your README and demo video so it doesn't look like you missed the number.

### Task 0.1 — Repo + scaffolding + meta files
```
Set up a new git repository for a voice-enabled RAG project with this structure:

/backend/src, /backend/scripts, /frontend/src
requirements.txt (empty for now), package.json for a Vite + React frontend

Copy in these four files at the repo root exactly as given (do not modify their content):
context.md, process.md, coding_conventions.md, README.md

Create .gitignore covering Python (venv, __pycache__, .env) and Node (node_modules, dist, .env).
Create backend/.env.example and frontend/.env.example with placeholder keys:
SARVAM_API_KEY=
QDRANT_URL=
QDRANT_API_KEY=
GENERATION_API_KEY=
GENERATION_MODEL=
(frontend) VITE_API_BASE_URL=

Initialize git, commit as "phase0: repo scaffolding".
After finishing, update process.md's STATUS SNAPSHOT and LOG per the template in that file.
```

### Task 0.2 — API account setup (manual — a human does this, not the agent)
Do these yourself, in parallel with Task 0.1:
1. **Sarvam AI**: sign up at sarvam.ai → dashboard → generate an API key. Free credits are
   included on signup, enough for hackathon-scale testing.
2. **Qdrant**: for the fastest path, run it locally via Docker (`docker run -p 6333:6333
   qdrant/qdrant`) during development. Before deployment, spin up a **Qdrant Cloud free-tier
   cluster** (qdrant.tech/cloud) so your deployed backend has a reachable vector DB — a
   localhost Qdrant won't be reachable from your live link.
3. **Generation API**: create an account with a fast-inference provider (e.g. Groq) and
   generate an API key. Pick a small/fast model given the latency budget.
4. **Hugging Face** (optional but recommended): create an account so dataset downloads aren't
   rate-limited.
5. Put every key into `backend/.env` (never commit this file) and fill in `context.md`'s
   "Team / links" table with who holds which key.

### Task 0.3 — Confirm dataset access
```
Read context.md for dataset details. Write a small script at backend/scripts/inspect_dataset.py
that:
1. Loads the "hi" (Hindi) config of ai4bharat/MSMARCO-XI from Hugging Face using the `datasets`
   library, split="train", with streaming=True so it doesn't try to download all 55GB.
2. Prints the first 3 examples' keys and a truncated view of one full example (query, one
   passage, one answer).
3. Prints the total row count if available without a full download.

Run it and paste the output into process.md under a new LOG entry, plus decide and record in
context.md which language(s) and how many rows you're actually going to index for the demo
(recommend: 1-3 languages, a few thousand passages each — enough to demo real retrieval without
an hours-long ingestion job).
Follow coding_conventions.md. Update process.md when done.
```

---

## Phase 1 — Data Ingestion & Chunking (~2–3 hrs)

### Task 1.1 — Chunking strategies module
```
Read context.md and coding_conventions.md first.

Create backend/src/chunking.py implementing at least these chunking strategies as separate,
independently callable functions, each returning a list of chunk dicts with fields
{text, chunk_id, source_doc_id, language, strategy, metadata}:

1. passage_native(): treat each MSMARCO passage as one chunk, unmodified (baseline).
2. fixed_size(text, size_tokens, overlap_tokens): token-based fixed windows with configurable
   overlap. Use tiktoken or a simple whitespace/word tokenizer if tiktoken isn't a good fit for
   Indic scripts — justify the tokenizer choice in a code comment.
3. semantic(text, embedding_model): split at sentence boundaries, embed each sentence, and cut
   a new chunk when cosine similarity between consecutive sentence embeddings drops below a
   threshold. Use sentence-transformers or the same embedding model as the retrieval pipeline.
4. hierarchical(text): produce small "child" chunks (for retrieval precision) each tagged with
   a reference to a larger "parent" chunk/passage (for generation context) — return both, with
   parent_id linking child to parent.

Every chunk's metadata dict must include: language, source query id (if available), and
strategy name, so retrieval can filter/compare across strategies later.

Do not implement your own tokenizer or embedding model from scratch — use existing libraries
per coding_conventions.md.

Write a docstring-level comparison note at the top of the file explaining the tradeoff of each
strategy (precision vs. context, cost, when each wins) — this doubles as your justification for
the "chunking should be vast" requirement in the submission.

Update process.md when done.
```

### Task 1.2 — Embedding + indexing into Qdrant
```
Read context.md, coding_conventions.md, and backend/src/chunking.py first.

Create backend/scripts/ingest.py that:
1. Loads the dataset subset decided in Task 0.3 (from context.md).
2. Runs it through all four chunking strategies from chunking.py, tagging each resulting chunk
   with its strategy name.
3. Embeds all chunks using bge-m3 (or the multilingual model chosen in context.md) via
   sentence-transformers or the model's official client.
4. Creates a Qdrant collection with a payload schema including: text, language, strategy,
   source_doc_id, parent_id (nullable). Upserts all chunks with their embeddings.
5. Is idempotent — safe to re-run without duplicating points (use deterministic point IDs,
   e.g. a hash of text+strategy).
6. Logs progress (chunks processed / total) and total wall-clock time at the end.

This is an offline batch job, not latency-critical — but it must be async-safe or batched so it
doesn't time out on your dataset subset size.

Run it against your chosen subset and report the resulting Qdrant point count in a new
process.md LOG entry. Update context.md's dataset section with the final numbers.
```

### Task 1.3 — Retrieval service (hybrid + strategy comparison)
```
Read context.md, coding_conventions.md, and the ingest script first.

Create backend/src/retrieval.py with an async function
retrieve(query: str, top_k: int = 5, language: str | None = None, strategy: str | None = None)
that:
1. Embeds the query with the same model used in ingest.py.
2. Runs a dense vector search against Qdrant, optionally filtered by language/strategy via
   payload filters.
3. Also runs a sparse BM25-style search (use rank_bm25 or Qdrant's built-in sparse vector
   support if available) over the same chunk set.
4. Fuses dense + sparse results with reciprocal rank fusion and returns the top_k merged
   results with their scores.
5. If using hierarchical chunks, resolves child hits back to their parent chunk for the context
   actually passed to generation.
6. Times each sub-step (embed, dense search, sparse search, fusion) and returns those timings
   alongside the results — this feeds Phase 5's latency analytics.

Write a small script backend/scripts/compare_strategies.py that runs a handful of sample
queries against each chunking strategy separately and prints retrieved-passage relevance
side-by-side (manual eyeball comparison is fine given the time budget) — this is your evidence
for "real thought put into chunking" in the submission.

Update process.md when done.
```

---

## Phase 2 — Speech-to-Text (~1 hr)

### Task 2.1 — Sarvam STT client
```
Read context.md and coding_conventions.md first.

Create backend/src/stt.py with an async function transcribe(audio_bytes: bytes, language_hint:
str | None = None) -> dict returning {text, detected_language, latency_ms}.

Use Sarvam's REST API for files under 30s (this is a voice-Q&A use case, so utterances should
be short) via their official Python SDK if available, else httpx directly. Read SARVAM_API_KEY
from environment. Wrap the call with a timeout (e.g. 5s) and one retry on transient failure
(use tenacity, per coding_conventions.md — don't hand-roll retry logic).

Return a clear error object (not a raised exception that crashes the request) if transcription
fails, so the API layer can degrade gracefully.

Write a tiny manual test script backend/scripts/test_stt.py that transcribes a sample WAV file
(record one yourself, a few seconds, any language in your dataset subset) and prints the result.
Update process.md with the test result and observed latency.
```

### Task 2.2 — FastAPI endpoint for audio upload
```
Read context.md, coding_conventions.md, and stt.py first.

Create backend/src/main.py (if not already started) with a FastAPI app and a POST
/api/ask endpoint that accepts multipart/form-data audio upload, calls stt.transcribe(), and
for now (until Phase 3 wires up retrieval+generation) just returns the transcript and its
latency as JSON. Add CORS middleware allowing the frontend's origin (read from an env var).

Add basic request validation (file size limit, accepted audio mime types) and a health check
endpoint GET /api/health.

Update process.md when done — note that this is a partial endpoint, full pipeline comes in
Phase 3.
```

---

## Phase 3 — Retrieval + Generation + Harness (~2 hrs)

### Task 3.1 — Generation service
```
Read context.md, coding_conventions.md, and retrieval.py first.

Create backend/src/generation.py with an async function
generate(query: str, context_chunks: list[dict]) -> dict returning {answer, latency_ms}.

Build a prompt that instructs the model to answer ONLY from the provided context chunks, and to
explicitly say it doesn't know if the context doesn't contain the answer (this is the seed for
Phase 4's grounding guardrail — make it easy for the guardrail layer to detect an "I don't
know"-style response). Call the generation API chosen in context.md, with a timeout and one
retry via tenacity.

Update process.md when done.
```

### Task 3.2 — Harness: orchestrate STT → retrieve → generate
```
Read context.md, coding_conventions.md, stt.py, retrieval.py, and generation.py first.

Create backend/src/harness.py implementing the orchestration as an explicit multi-step
pipeline (use LangGraph if you have time to learn it quickly; otherwise a plain Python state
machine class with named steps is acceptable and still satisfies "structured orchestration" —
document which you chose and why in a comment at the top of the file).

Steps: transcribe_audio -> validate_input (Phase 4 hook) -> retrieve_context ->
check_retrieval_confidence (Phase 4 hook) -> generate_answer -> check_grounding (Phase 4 hook)
-> return_result.

Each step must:
- Have its own try/except with a specific fallback (e.g. STT failure -> return "couldn't
  understand audio, please try again", not a 500 error).
- Record its own latency into a shared timings dict that gets returned alongside the final
  answer.
- Be independently retryable without re-running prior steps.

Wire this into main.py's /api/ask endpoint, replacing the partial version from Task 2.2. The
endpoint should return: {transcript, answer, sources (chunk ids/text used), timings (per-stage
ms), guardrail_flags}.

Update process.md when done — this is the core pipeline, flag clearly if anything is still a
stub waiting on Phase 4.
```

---

## Phase 4 — Guardrails (~1–1.5 hrs)

### Task 4.1 — Input guardrails
```
Read context.md, coding_conventions.md, and harness.py first.

Create backend/src/guardrails.py with:
1. is_unsafe_input(text: str) -> bool — a lightweight check for unsafe/inappropriate content.
   Use a small existing moderation approach (an LLM-as-judge call with a strict yes/no prompt is
   fine given the time budget — don't build a custom classifier from scratch).
2. is_offtopic(text: str, domain_description: str) -> bool — checks whether the query is
   plausibly answerable from the MSMARCO-XI domain (general knowledge/QA passages) vs. clearly
   unrelated. Same approach as above is fine.

Wire both into harness.py's validate_input step. If either trips, short-circuit the pipeline
(skip retrieval/generation entirely) and return a clear refusal message plus the specific
guardrail_flag that fired.

Update process.md when done.
```

### Task 4.2 — Retrieval confidence + grounding/hallucination checks
```
Read context.md, coding_conventions.md, and harness.py first.

Add to guardrails.py:
1. is_low_confidence_retrieval(results: list, threshold: float) -> bool — checks whether the
   top retrieval score is below a threshold you pick empirically (test with a few
   clearly-in-domain vs. clearly-out-of-domain queries and record the threshold you land on,
   with reasoning, in process.md).
2. is_grounded(answer: str, context_chunks: list[dict]) -> bool — checks whether the generated
   answer is actually supported by the retrieved context. Simplest reliable approach given the
   time budget: a second short LLM call asking "is this answer fully supported by this context,
   yes/no" — don't build a custom NLI model from scratch.

Wire both into harness.py: low retrieval confidence -> skip generation, return "I don't have
enough grounded information to answer that." Failed grounding check -> don't return the
ungrounded answer, return the same fallback instead.

Write backend/scripts/test_guardrails.py with a handful of test cases (one off-topic query, one
unsafe query, one in-domain query with a confident answer, one in-domain query worded to bait a
hallucination) and print pass/fail for each guardrail. Paste results into process.md.
```

---

## Phase 5 — Latency Instrumentation & Analytics (~45 min)

### Task 5.1 — Benchmark script
```
Read context.md, coding_conventions.md, and harness.py first.

Create backend/scripts/benchmark_latency.py that:
1. Runs at least 30 test queries (mix of text-based, bypassing STT, to isolate
   retrieval-through-output latency per the interpretation recorded in context.md/Task 0.0)
   through the harness.
2. Collects per-stage timings (from the timings dict harness.py already returns) across all
   runs.
3. Computes P50, P70, and P100 (max) for each stage AND for the retrieval-only sub-total, using
   numpy.percentile — don't hand-roll percentile math.
4. Writes a report to backend/reports/latency_report.md (or .json) with a table of stage ->
   P50/P70/P100, plus a one-line summary of whether the 200ms target was met for the
   retrieval-through-output interpretation.

Run it and paste the resulting numbers into process.md and into README.md's (new) "Latency
Results" section.
```

---

## Phase 6 — Frontend (React) (~2 hrs — can start in parallel with Phase 1–3)

### Task 6.1 — Scaffold + mic capture
```
Read context.md and coding_conventions.md first.

Scaffold a React app in /frontend using Vite. Build a single main screen component
(components/VoiceQA.jsx) with:
- A record button using the browser MediaRecorder API to capture microphone audio.
- Visual states: idle, recording, uploading, waiting-for-answer, showing-answer, error,
  guardrail-refused.
- No backend calls yet in this task — stub the API call with a fake delayed response so the UI
  states can be built and tested independently of the backend being ready.

Follow the React conventions in coding_conventions.md (functional components, one component per
file, no scattered fetch calls). Update process.md when done.
```

### Task 6.2 — API integration
```
Read context.md, coding_conventions.md, and the current backend /api/ask contract (from
harness.py / main.py — read those files, don't assume the shape) first.

Create frontend/src/api/client.js as the single module that talks to the backend: a function
askQuestion(audioBlob) that POSTs to VITE_API_BASE_URL + /api/ask and returns the parsed
{transcript, answer, sources, timings, guardrail_flags} response.

Wire VoiceQA.jsx to use the real client instead of the Task 6.1 stub. Render: the transcript,
the answer, which chunks/sources it came from, and — if a guardrail fired — a clear,
non-technical message explaining why the system didn't answer (not a raw error dump).

Update process.md when done.
```

### Task 6.3 — Demo polish
```
Read context.md and coding_conventions.md first.

Polish frontend/src/components/VoiceQA.jsx for demo-readiness:
- Loading state shows which pipeline stage is active if that data is available (transcribing /
  retrieving / generating), not just a generic spinner.
- Show the per-stage latency numbers somewhere visible (small, unobtrusive) — this is a strong,
  cheap thing to show off in the demo video given latency is an explicit grading criterion.
- Make sure error and guardrail-refusal states look intentional, not broken — this is often
  what differentiates hackathon submissions in a live demo.

Update process.md when done.
```

---

## Phase 7 — Deployment (~45 min–1 hr)

### Task 7.1 — Backend deployment
```
Read context.md and coding_conventions.md first.

Add a Dockerfile for the backend (Python slim base, install requirements.txt, run uvicorn).
Deploy to Railway or Render (whichever you set up an account on) with the environment variables
from backend/.env filled in via the platform's secrets UI — never commit real keys.

Point QDRANT_URL at the Qdrant Cloud free-tier cluster from Task 0.2, not localhost.

Verify the deployed /api/health endpoint responds, then verify /api/ask works end-to-end with
a real audio file against the deployed URL (not localhost).

Update context.md's "Team / links" table with the live backend URL. Update process.md.
```

### Task 7.2 — Frontend deployment
```
Read context.md first.

Deploy /frontend to Vercel or Netlify. Set VITE_API_BASE_URL in the platform's environment
variable settings to point at the deployed backend URL from Task 7.1. Verify the live frontend
successfully completes a full voice question end-to-end against the deployed backend.

Update context.md and README.md with the live link. Update process.md — mark STATUS SNAPSHOT
"Deployed?" as yes.
```

---

## Phase 8 — Documentation & Submission (~30–45 min)

### Task 8.1 — Finalize README
```
Read context.md, process.md, and the actual current codebase structure first (don't assume —
verify file paths and script names match what's actually in the repo).

Update README.md to reflect final reality: correct repo structure, correct setup steps that
actually work if someone clones fresh, the final latency report numbers from Phase 5, the live
link, and the team section. Remove any placeholder text that's still unfilled.
```

### Task 8.2 — Submission checklist (manual, not an agent task)
- [ ] Submission form filled: https://forms.gle/MNvCjcv23Hn2Eeu58
- [ ] GitHub repo link (public, README complete)
- [ ] Live working link (tested fresh, not just "worked once")
- [ ] Video 1 (90s team/process video) recorded
- [ ] Video 2 (full end-to-end demo video) recorded
- [ ] Both videos posted to Instagram by every team member (at least 1 public account)
- [ ] Both videos posted to X by every team member
- [ ] Every single post, every platform, every member includes `#RAGInGoa`
- [ ] Final gut-check: does the demo video show the guardrails actually refusing something,
      and show the latency numbers? Both are explicit grading criteria — don't bury them.
