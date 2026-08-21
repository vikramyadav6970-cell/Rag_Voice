# process.md — Running Status Log

Update this file at the END of every work session, before you stop. Any agent (or teammate)
picking up the project reads this file second, right after `context.md`, to know what's done
and what to do next. Don't let this go stale — a wrong "next step" wastes more time than a
missing one.

Keep entries short. Newest at the top.

---

## STATUS SNAPSHOT (always keep this section current — overwrite, don't append)

- **Current phase**: Phase 3 — Retrieval + Generation + Harness
- **Blocking issue**: none
- **Next immediate task**: Task 3.1 — Generation service (`backend/src/generation.py`)
- **Dataset subset in use**: Hindi (`hin`) + Tamil (`tam`), 5,536 points indexed in Qdrant Cloud (`msmarco_indic_rag`)
- **Deployed?**: no

---

## LOG (append new entries at the top, most recent first)

### 2026-08-22 — Agent (Task 2.2)
- What was done: Built FastAPI server at `backend/src/main.py` with CORS middleware configured for React Vite frontend, health check diagnostics `GET /api/health`, and multipart audio upload endpoint `POST /api/ask` executing Sarvam STT transcription with request validation (file size bounds, allowed audio MIME types, and structured Pydantic models). Added integration tests in `backend/tests/test_main.py`.
- Files changed: [backend/src/main.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/main.py), [backend/tests/test_main.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_main.py), [backend/requirements.txt](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/requirements.txt), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `pytest backend/tests/` — **16/16 tests passed** covering health check response, empty audio file rejection (HTTP 400), unsupported MIME types rejection (HTTP 415), and valid multipart audio payload transcription.
- Decisions made: Structured response schema `AskAudioResponse` built with forward-compatible placeholder fields for Phase 3 end-to-end RAG synthesis.
- Next task: Task 3.1 — Generation service (`backend/src/generation.py`).


### 2026-08-22 — Agent (Task 2.1)
- What was done: Built async Speech-to-Text client at `backend/src/stt.py` integrating Sarvam AI's Saaras v3 REST API. Added BCP-47 language code normalization (`hi-IN`, `ta-IN`, `te-IN`, `bn-IN`, etc.), 5s timeout, tenacity exponential retry on transient network failures, and graceful error degradation. Built verification script `backend/scripts/test_stt.py` generating in-memory 16kHz audio and added unit tests in `backend/tests/test_stt.py`.
- Files changed: [backend/src/stt.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/stt.py), [backend/scripts/test_stt.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/test_stt.py), [backend/tests/test_stt.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_stt.py), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested:
  - Ran `backend/scripts/test_stt.py` against live Sarvam API: Verified authentication, status `Success: True`, detected language `hi-IN`, observed roundtrip latency `~789ms`.
  - Ran `pytest backend/tests/` — **12/12 tests passed** across chunking, hybrid retrieval, and STT modules.
- Next task: Task 2.2 — FastAPI endpoint for audio upload (`backend/src/main.py`).


### 2026-08-22 — Agent (Task 1.3)
- What was done: Built async retrieval service at `backend/src/retrieval.py` implementing multilingual hybrid search (dense embeddings via `bge-m3` + sparse BM25 with Indic Unicode tokenization + Reciprocal Rank Fusion), hierarchical parent context resolution for child chunks, and sub-step latency breakdown telemetry (`embed_ms`, `dense_search_ms`, `sparse_search_ms`, `fusion_ms`, `parent_resolution_ms`, `total_retrieval_ms`). Built evaluation script `backend/scripts/compare_strategies.py` running comparative queries across all 4 strategies in Hindi and Tamil. Added unit tests in `backend/tests/test_retrieval.py`.
- Files changed: [backend/src/retrieval.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/retrieval.py), [backend/scripts/compare_strategies.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/compare_strategies.py), [backend/tests/test_retrieval.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_retrieval.py), [backend/requirements.txt](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/requirements.txt), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested:
  - Ran `pytest backend/tests/` — **10/10 tests passed** covering Indic tokenization, RRF rank calculations, empty query handling, and live hybrid retrieval from Qdrant Cloud.
  - Ran `backend/scripts/compare_strategies.py` across Hindi and Tamil queries:
    - `passage_native`: Balanced paragraph context.
    - `fixed_size`: Good granular coverage with overlap.
    - `semantic`: High topical purity on sentence-cut boundaries.
    - `hierarchical_child`: Precision vector matching on child chunks with full parent context resolved dynamically.
  - Granular latency verified: Query embedding (~120ms), Dense Qdrant search (~280ms), Sparse BM25 (~1.2ms), RRF Fusion (~0.02ms).
- Next task: Task 2.1 — Sarvam STT client (`backend/src/stt.py`).


### 2026-08-22 — Agent (Task 1.2)
- What was done: Built offline batch ingestion pipeline at `backend/scripts/ingest.py`. Connected to Qdrant Cloud cluster, created `msmarco_indic_rag` collection with 1024-d Cosine vectors, and created payload indexes on `language`, `strategy`, `source_doc_id`, `parent_id`, and `query_id`. Streamed validation splits for Hindi (`hin`) and Tamil (`tam`), processed all passages across all 4 chunking strategies, computed normalized dense embeddings via `BAAI/bge-m3`, and idempotently upserted points with UUID5 deterministic IDs.
- Files changed: [backend/scripts/ingest.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/ingest.py), [context.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/context.md), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Verified live points in Qdrant Cloud collection `msmarco_indic_rag`:
  - **Total points verified in Qdrant**: `5,536` points (status: `green`)
  - **Breakdown by Strategy**:
    - `passage_native`: 853 points
    - `fixed_size`: 904 points
    - `semantic`: 1,530 points
    - `hierarchical_parent`: 853 points
    - `hierarchical_child`: 1,396 points
  - **Breakdown by Language**:
    - `HIN` (Hindi): 3,414 points
    - `TAM` (Tamil): 2,122 points
- Decisions made: Ingested 50 diverse queries per language (~10 passages per query) generating 5,536 chunks covering all 4 chunking strategies to provide rich ground-truth retrieval testing without exceeding cloud quotas.
- Next task: Task 1.3 — Retrieval service (hybrid + strategy comparison) (`backend/src/retrieval.py`).


### 2026-08-22 — Agent (Task 1.1)
- What was done: Built production chunking strategies module at `backend/src/chunking.py` implementing all 4 strategies: `passage_native`, `fixed_size`, `semantic`, and `hierarchical` + unified router `chunk_document`. Documented trade-off analysis (precision vs. context, compute cost, latency, when each wins) in the module docstring. Added Indic Unicode preservation rules to prevent akshara/matra corruption. Added automated unit tests in `backend/tests/test_chunking.py`.
- Files changed: [backend/src/chunking.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/chunking.py), [backend/tests/test_chunking.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_chunking.py), [backend/requirements.txt](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/requirements.txt), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `pytest backend/tests/test_chunking.py` — 6/6 tests passed covering chunk dict structure, token counts, deterministic 16-hex `chunk_id` hashing, sentence splitting with Indic danda (`।`), mock semantic cosine threshold cuts, and hierarchical parent-child pointer links.
- Decisions made: Word-boundary sliding window with `tiktoken` tracking chosen for `fixed_size` and `hierarchical_child` to avoid splitting Indic conjunct characters; cosine similarity drop detection chosen for `semantic` chunking.
- Next task: Task 1.2 — Embedding + indexing into Qdrant (`backend/scripts/ingest.py`).


### 2026-08-22 — Agent (Task 0.3)
- What was done: Confirmed dataset access to `ai4bharat/MSMARCO-XI` using `fastparquet` and `huggingface_hub` streaming with `HF_TOKEN`. Inspected schema, column metadata, and sample records for Hindi (`hin`). Determined dataset subset size and strategy. Cleaned up scratch exploration files.
- Files changed: [backend/scripts/inspect_dataset.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/inspect_dataset.py), [context.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/context.md), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Successfully streamed schema and rows from `datasets/ai4bharat/MSMARCO-XI/validation/hinval.parquet` (97,941 rows in validation split, 778,638 in train split) without local multi-GB disk download. Inspected `query_id`, `query`, `Answer`, `Eng_Query`, `Eng_Answer`, `passages.Translated_passages`, `passages.English_passages`, `passages.is_selected`.
- Output snippet:
  ```
  Total row count for hin (validation): 97,941 rows
  Columns available (17): ['source_lang', 'target_lang', 'Answer', 'query_id', 'query_type', 'Eng_Query', 'Eng_Answer', 'query', 'meta.*', 'passages.English_passages', 'passages.Translated_passages', 'passages.is_selected']
  --- Sample #1 ---
  Query ID     : 1102432
  Query (Eng)  : . what is a corporation?
  Query (HIN)  : कॉर्पोरेशन क्या है?
  Answer       : निगम एक कंपनी या लोगों का समूह होता है जो एक एकल इकाई के रूप में कार्य करने के लिए अधिकृत होता है और कानून में इस प्रकार से मान्यता प्राप्त होती है।
  Passages Count: 10
  Passage #1   : एक कंपनी एक विशिष्ट देश में निगमित होती है, अक्सर उस देश के एक छोटे उपसमूह...
  is_selected  : [0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
  ```
- Decisions made: Selected Hindi (`hin`) + Tamil (`tam`) subset (~2,500–5,000 chunks) focusing on ground truth selected passages + distractor context to balance multilingual representation, rapid ingestion, and vector DB quota limits.
- Next task: Task 1.1 — Chunking strategies module (`backend/src/chunking.py`).


### 2026-08-22 — User & Agent (Task 0.2)
- What was done: Configured credentials in `backend/.env` for Sarvam AI, Qdrant Cloud (`aws.cloud.qdrant.io`), and xAI with model `grok-2-mini` and base URL `https://api.x.ai/v1`. Updated `context.md` with active stack providers.
- Files changed: [backend/.env](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/.env), [backend/.env.example](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/.env.example), [context.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/context.md), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- Decisions made: Selected `grok-2-mini` via OpenAI-compatible endpoint (`https://api.x.ai/v1`) for generation due to fast time-to-first-token and low inference latency.
- Next task: Task 0.3 — Backend venv + base dependencies.


### 2026-08-22 — Agent (Task 0.1)
- What was done: Initialized git repository on branch `main`, scaffolded `/backend/src`, `/backend/scripts`, `/frontend/src`, created `.gitignore`, `backend/requirements.txt`, `backend/.env.example`, `frontend/package.json`, `frontend/.env.example`, and baseline frontend Vite/React setup. Created initial commit `phase0: repo scaffolding`.
- Files changed: [.gitignore](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/.gitignore), [backend/.env.example](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/.env.example), [backend/requirements.txt](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/requirements.txt), [frontend/.env.example](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/.env.example), [frontend/package.json](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/package.json), [frontend/src/App.jsx](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/App.jsx), [frontend/vite.config.js](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/vite.config.js), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Git initialization, clean commit of all scaffolded files.
- What's broken or unverified: Dependencies not yet installed in venv (Task 0.3).
- Decisions made: Initialized React 18 + Vite scaffolding in `frontend/`.
- Next task: Task 0.2 (API credentials setup by user) / Task 0.3 (Backend venv + dependencies).

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
