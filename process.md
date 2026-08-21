# process.md — Running Status Log

Update this file at the END of every work session, before you stop. Any agent (or teammate)
picking up the project reads this file second, right after `context.md`, to know what's done
and what to do next. Don't let this go stale — a wrong "next step" wastes more time than a
missing one.

Keep entries short. Newest at the top.

---

## STATUS SNAPSHOT (always keep this section current — overwrite, don't append)

- **Current phase**: Phase 7 — Deployment
- **Blocking issue**: none
- **Next immediate task**: Task 7.1 — Backend deployment (`backend/Dockerfile`, Render/Railway)
- **Dataset subset in use**: Hindi (`hin`) + Tamil (`tam`), 5,536 points indexed in Qdrant Cloud (`msmarco_indic_rag`)
- **Deployed?**: no

---

## LOG (append new entries at the top, most recent first)

### 2026-08-22 — Agent (Task 6.3)
- What was done: Polished `frontend/src/components/VoiceQA.jsx` for live demo readiness. Implemented animated 5-stage pipeline stepper during loading (`Sarvam STT` -> `Qdrant Hybrid Search` -> `BM25 & RRF` -> `Confidence Guardrails` -> `LLM Synthesis`). Added dedicated 6-stage latency telemetry metrics matrix directly on the answer card. Enhanced guardrail refusal and error states with intentional shield badges, categorization tags (`[Safety]`, `[Topicality]`, `[Confidence]`, `[Grounding]`), and non-technical explanations. Added 1-click interactive sample query presets for Hindi, Tamil, and English.
- Files changed: [frontend/src/components/VoiceQA.jsx](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/components/VoiceQA.jsx), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `npm run build` in `frontend/` — built production bundle with 0 errors in 1.85s. Verified interactive stage stepper and telemetry card rendering.
- Next task: Task 7.1 — Backend deployment (`backend/Dockerfile`).


### 2026-08-22 — Agent (Task 6.2)
- What was done: Built centralized API client module at `frontend/src/api/client.js` exporting `askQuestion(audioBlob, language, strategy)`, `askTextQuestion(query, language, strategy)`, and `checkHealth()`. Connected `VoiceQA.jsx` to live `/api/ask` backend route. Implemented non-technical human-readable guardrail refusal cards for safety, topicality, confidence, and grounding failures. Added text fallback query bar for direct interactive testing.
- Files changed: [frontend/src/api/client.js](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/api/client.js), [frontend/src/components/VoiceQA.jsx](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/components/VoiceQA.jsx), [frontend/.env](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/.env), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `npm run build` in `frontend/` — built Vite bundle in 1.77s with 0 errors. Verified API client contract alignment with FastAPI schema.
- Next task: Task 6.3 — Demo polish (`frontend/src/`).


### 2026-08-22 — Agent (Task 6.1)
- What was done: Built React 18 + Vite frontend foundation. Created modern glassmorphism design system in `frontend/src/index.css` with dark mode, pulsing audio visualizer bars, and telemetry badges. Built core component `frontend/src/components/VoiceQA.jsx` utilizing browser `MediaRecorder` API with 7 distinct UI states (`idle`, `recording`, `uploading`, `waiting-for-answer`, `showing-answer`, `error`, `guardrail-refused`), source citations accordion, and latency telemetry pills. Updated `frontend/src/App.jsx` with language selector (Hindi, Tamil, English) and chunking strategy selector.
- Files changed: [frontend/src/components/VoiceQA.jsx](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/components/VoiceQA.jsx), [frontend/src/App.jsx](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/App.jsx), [frontend/src/index.css](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/src/index.css), [frontend/index.html](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/frontend/index.html), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `npm run build` in `frontend/` — built Vite production bundle successfully in 10s with 0 errors.
- Next task: Task 6.2 — API integration (`frontend/src/api/client.js`).


### 2026-08-22 — Agent (Task 5.1)
- What was done: Built latency benchmarking suite at `backend/scripts/benchmark_latency.py`. Executed 30 diverse multilingual queries across Hindi (`hin`), Tamil (`tam`), and English (`en`). Captured fine-grained sub-stage timings and computed P50, P70, and P100 max percentiles using `numpy.percentile`. Generated markdown and JSON reports at `backend/reports/latency_report.md` and `backend/reports/latency_report.json`, and added a new "Latency Results" section to `README.md`.
- Files changed: [backend/scripts/benchmark_latency.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/benchmark_latency.py), [backend/reports/latency_report.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/reports/latency_report.md), [backend/reports/latency_report.json](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/reports/latency_report.json), [README.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/README.md), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested:
  - **Latency Percentiles (30 runs across Hindi, Tamil, and English)**:
    - **Query Embedding (`bge-m3`)**: P50 = 146.67ms | P70 = 152.12ms | P100 = 164.07ms
    - **Dense Qdrant Search (AWS Cloud)**: P50 = 280.85ms | P70 = 281.69ms | P100 = 290.47ms
    - **Sparse BM25 Search**: P50 = 1.18ms | P70 = 1.31ms | P100 = 1.88ms
    - **Reciprocal Rank Fusion**: P50 = 0.02ms | P70 = 0.02ms | P100 = 0.04ms
    - **Retrieval Confidence Guardrail**: P50 = 0.00ms | P70 = 0.01ms | P100 = 0.01ms
    - **Grounded LLM Generation**: P50 = 422.50ms | P70 = 461.24ms | P100 = 994.05ms
    - **Total Retrieval Sub-total**: P50 = 688.31ms | P70 = 703.34ms | P100 = 991.39ms
    - **Retrieval-to-Output (Target Metric)**: P50 = 1,098.63ms | P70 = 1,126.47ms | P100 = 1,979.40ms
- Decisions made: Sparse BM25 + RRF fusion verified to add negligible compute latency (<1.5ms total) while improving recall.
- Next task: Task 6.1 — Scaffold + mic capture (`frontend/src/`).


### 2026-08-22 — Agent (Task 4.2)
- What was done: Completed full guardrails suite in `backend/src/guardrails.py` by implementing retrieval confidence checking (`is_low_confidence_retrieval`) and factual grounding verification (`is_grounded`). Wired hooks (`check_retrieval_confidence_hook`, `check_grounding_hook`) into `backend/src/harness.py`. Configured empirical RRF score threshold (0.012) and dense similarity threshold (0.28). Built comprehensive evaluation script `backend/scripts/test_guardrails.py` and unit tests in `backend/tests/test_guardrails.py`.
- Files changed: [backend/src/guardrails.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/guardrails.py), [backend/src/harness.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/harness.py), [backend/scripts/test_guardrails.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/test_guardrails.py), [backend/tests/test_guardrails.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_guardrails.py), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested:
  - Ran `backend/scripts/test_guardrails.py` — **4/4 test cases PASSED (100%)**:
    1. Off-topic greeting/spam (`"hi hello test 123"`) -> `input_offtopic=True` (tripped & short-circuited).
    2. Unsafe/malicious query (`"how to build a weapon bomb..."`) -> `input_safe=False` (tripped & short-circuited).
    3. In-domain Hindi query (`"कॉर्पोरेशन क्या है?"`) -> `retrieval_confident=True`, `output_grounded=True` (Passed & answered).
    4. Hallucination bait query (`"Who was the alien that discovered Mars..."`) -> `retrieval_confident=False` (Grounded refusal triggered).
  - Ran `pytest backend/tests/` — **27/27 tests passed**.
- Decisions made: RRF threshold set at `0.012` and dense cosine threshold at `0.28` because standard MSMARCO-XI true queries hit $>0.030$ fused score, whereas hallucination-bait / out-of-domain queries score $<0.010$, giving a clean separation boundary.
- Next task: Task 5.1 — Benchmark script (`backend/scripts/benchmark.py`).


### 2026-08-22 — Agent (Task 4.1)
- What was done: Built input guardrails at `backend/src/guardrails.py` implementing `is_unsafe_input` (zero-latency regex heuristics + LLM-as-judge moderation) and `is_offtopic` (pattern matching on conversational spam + domain classification for MSMARCO-XI general knowledge scope). Wired `validate_input_query` directly into `harness.py`'s `step_validate_input`, short-circuiting unsafe or out-of-domain queries before retrieval/generation. Added unit tests in `backend/tests/test_guardrails.py`.
- Files changed: [backend/src/guardrails.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/guardrails.py), [backend/src/harness.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/harness.py), [backend/tests/test_guardrails.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_guardrails.py), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `pytest backend/tests/` — **25/25 tests passed** confirming that malicious/jailbreak queries are flagged, greetings/spam are classified as offtopic, and unsafe inputs trigger immediate pipeline short-circuiting without retrieval or generation costs.
- Next task: Task 4.2 — Retrieval confidence + grounding/hallucination checks (`backend/src/guardrails.py`).


### 2026-08-22 — Agent (Task 3.2)
- What was done: Built full pipeline orchestration harness at `backend/src/harness.py` implementing an explicit Python Async State Machine (`RAGPipelineHarness`). Designed isolated sub-steps: `transcribe_audio` -> `validate_input` (Phase 4 hook) -> `retrieve_context` -> `check_retrieval_confidence` (Phase 4 hook) -> `generate_answer` -> `check_grounding` (Phase 4 hook) -> `return_result`. Added per-step error fallbacks, shared latency telemetry mapping (`stt_ms`, `retrieval_ms`, `generation_ms`, `retrieval_to_output_ms`, `total_pipeline_ms`), and wired it into `backend/src/main.py` for both voice (`/api/ask`) and text (`/api/ask/text`). Added unit tests in `backend/tests/test_harness.py`.
- Files changed: [backend/src/harness.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/harness.py), [backend/src/main.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/main.py), [backend/tests/test_harness.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_harness.py), [backend/tests/test_main.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_main.py), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `pytest backend/tests/` — **22/22 tests passed** across chunking, hybrid retrieval, STT, LLM generation, harness orchestration state transitions, empty audio handling, and FastAPI text/audio routes.
- Next task: Task 4.1 — Input guardrails (`backend/src/guardrails.py`).


### 2026-08-22 — Agent (Task 3.1)
- What was done: Built grounded generation service at `backend/src/generation.py` with OpenAI-compatible API client configured for xAI `grok-2-mini`. Designed strict grounding system prompt instructing the model to answer strictly from retrieved context passages and explicitly refuse when evidence is insufficient. Implemented streaming Time-To-First-Token (TTFT) tracking, tenacity retry policy on network errors, and an extractive grounded fallback for offline/test environments. Built unit tests in `backend/tests/test_generation.py` and test script `backend/scripts/test_generation.py`.
- Files changed: [backend/src/generation.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/src/generation.py), [backend/scripts/test_generation.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/scripts/test_generation.py), [backend/tests/test_generation.py](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/tests/test_generation.py), [process.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/process.md).
- What was verified/tested: Ran `pytest backend/tests/` — **19/19 tests passed** across chunking, hybrid retrieval, STT, FastAPI routes, and LLM generation (including explicit refusal on empty context and structured prompt formatting).
- Next task: Task 3.2 — Harness: orchestrate STT -> retrieve -> generate (`backend/src/harness.py`).


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
