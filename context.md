# context.md — Project Orientation

Read this file first. It does not change often — it's the "what and why," not the "what's done."
For current status, see `process.md`. For coding rules, see `coding_conventions.md`.

## What we're building

A voice-enabled RAG (Retrieval-Augmented Generation) system for HH Goa 2026 hackathon
Shortlisting Task 2. A user speaks a question → we transcribe it → retrieve relevant passages
from the MSMARCO-XI dataset via a vector DB → generate a grounded answer → return it.

Pipeline: **Voice input → Speech-to-text → Chunking/Retrieval (vector DB) → Answer generation**

## Source spec

Original task PDF requirements (do not deviate without updating this file):

1. **STT**: Use either Sarvam or ElevenLabs. We are using **Sarvam** (Saaras v3) — better fit
   for Indic-language/code-mixed audio, sub-150ms time-to-first-token in fast mode, and the
   dataset itself is Indic-language content.
2. **Chunking**: Must be "vast" — multiple strategies (fixed-size, semantic, hierarchical
   parent-child, metadata-aware), not one naive fixed-size splitter. Must justify the choices.
3. **Latency target**: Chunking + vector DB retrieval + everything through to final output
   under 200ms. (Flag: if this is meant to include LLM generation, that's extremely tight —
   confirm interpretation early; see Task 0.0 in PROMPTS.md.)
4. **Latency analytics**: Submit P50 / P70 / P100 latency numbers across a reasonable number
   of test queries, not a single best-case run. Per-stage timing, not just end-to-end.
5. **Harness**: Structured orchestration around the model — tool calls, retries, structured
   I/O, error recovery. Not a single raw prompt-in/text-out call.
6. **Guardrails**: Off-topic query handling, unsafe/inappropriate input handling, hallucination
   checks, answers-not-grounded-in-context checks. System must know when *not* to answer.

## Dataset

`ai4bharat/MSMARCO-XI` on Hugging Face — MS MARCO (queries, passages, answers) machine-translated
into ~13 Indic languages, organized by language subfolder (hi, ta, te, bn, mr, gu, kn, ml, pa, or,
as, ne, ur), ~55GB total across train/validation splits. Passages are already a natural retrieval
unit — treat that as your baseline chunk, not your only chunk.

**Demo Corpus Scope**: Ingesting ~3,000 query rows (translating to roughly 100K–150K raw chunks across all 4 chunking strategies, and significantly lower after passage deduplication) provides the ideal scope for high factual density, representative evaluation, and sub-second retrieval benchmarks without triggering cloud quota limits or compute bottlenecks. Full 55GB subset indexing is neither necessary nor intended for this demo tier.

## Tech stack decisions (and why)

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| STT | Sarvam (Saaras v3) | Indic-language + code-mix native, streaming, sub-150ms TTFT | ElevenLabs — weaker on Indic/code-mixed audio |
| Embeddings | bge-m3 (multilingual) | Covers all dataset languages, strong multilingual retrieval | English-only models (e5-small etc.) — wrong fit for Indic content |
| Vector DB | Qdrant Cloud | Managed AWS instance, metadata filtering, hybrid search, persistence | FAISS-only (no persistence/filtering); Pinecone |
| Generation | Sarvam AI `sarvam-105b` (OpenAI-compatible API) | Already-authenticated account, OpenAI-compatible, native Indic mastery, avoids provisioning new providers under deadline pressure | xAI / Groq — unprovisioned / quota-exhausted |
| Harness | LangGraph (or FastAPI state machine) | Explicit nodes, retries, structured state | Raw prompt-in/text-out call — disallowed by spec |
| Backend | Python (FastAPI) | Best library support for RAG/embeddings/vector DB clients | — |
| Frontend | React (Vite) | Explicit requirement | Next.js — not required here |
| Deployment | Backend: Railway/Render/Fly.io. Frontend: Vercel/Netlify | Fast to stand up, free tiers exist | — |

**Update this table if a decision changes — don't leave it stale.**

## Team / links (fill in)

- GitHub repo: https://github.com/vikramyadav6970-cell/Rag_Voice.git
- Live deployed link: `<pending deployment>`
- Sarvam API: Configured in `backend/.env` (Saaras v3)
- Vector DB instance URL: Qdrant Cloud (`aws.cloud.qdrant.io` configured in `backend/.env`)
- Generation API provider + model: xAI (`grok-2-mini` configured in `backend/.env`)


## Hard constraints

- Deadline: **August 22, 2026, 11:59 PM**. No resubmissions.
- Submission needs: GitHub repo link, live working link, 90s team/process video, full demo
  video, both videos posted on Instagram AND X by every team member with `#RAGInGoa`.
- **Dataset subset decision & indexed stats (Tasks 0.3 & 1.2)**:
  - Selected Languages: **Hindi (`hin`)** and **Tamil (`tam`)**.
  - Verified Indexed Points in Qdrant Cloud (`msmarco_indic_rag`): **5,536 total points**
    - Hindi: 3,414 chunks
    - Tamil: 2,122 chunks
    - `passage_native`: 853 chunks
    - `fixed_size`: 904 chunks
    - `semantic`: 1,530 chunks
    - `hierarchical_parent`: 853 chunks
    - `hierarchical_child`: 1,396 chunks
  - Embedding: `BAAI/bge-m3` (1024-dimensional normalized dense vectors).


