# Voice-Enabled RAG — HH Goa 2026, Shortlisting Task 2

A voice-enabled Retrieval-Augmented Generation system: speak a question, get a grounded
answer retrieved from the AI4Bharat MSMARCO-XI dataset.

> Built for HH Goa 2026 hackathon shortlisting. See `context.md` for full spec and design
> decisions, `process.md` for current build status.

## Architecture

```
Voice input (browser mic)
   │
   ▼
Speech-to-Text (Sarvam Saaras v3, streaming)
   │
   ▼
Query embedding (bge-m3, multilingual)
   │
   ▼
Hybrid retrieval (Qdrant: dense + sparse, metadata-filtered)
   │
   ▼
Input/retrieval guardrails (off-topic filter, confidence threshold)
   │
   ▼
Answer generation (harnessed via LangGraph — retries, structured I/O)
   │
   ▼
Output guardrails (grounding / hallucination check)
   │
   ▼
Answer returned to frontend
```

<!-- Replace with an actual diagram image once the pipeline is stable -->

## Tech stack

- **STT**: Sarvam AI (Saaras v3)
- **Embeddings**: `BAAI/bge-m3` (1024-dimensional normalized dense vectors)
- **Vector DB**: Qdrant Cloud (`msmarco_indic_rag`, 5,536 points)
- **Generation**: xAI (`grok-2-mini` / fast inference streaming)
- **Harness**: Explicit Async State Machine (`RAGPipelineHarness`)
- **Guardrails**: Safety moderation, domain classification, retrieval confidence filtering, and factual grounding checks
- **Backend**: FastAPI (Python 3.14)
- **Frontend**: React 18 (Vite)
- **Deployment**: Railway / Render / Vercel


## Repo structure

```
/backend
  /src
    stt.py
    chunking.py
    retrieval.py
    generation.py
    guardrails.py
    harness.py
    main.py            # FastAPI app entrypoint
  /scripts
    ingest.py           # offline: chunk + embed + index dataset subset
    benchmark_latency.py # runs test queries, outputs P50/P70/P100
  requirements.txt
  .env.example
/frontend
  /src
    /components
    /api
  package.json
context.md
process.md
coding_conventions.md
README.md (this file)
```

## Setup

### Prerequisites / accounts needed

| Service | What you need | Where |
|---|---|---|
| Sarvam AI | API key (free credits on signup) | https://www.sarvam.ai |
| Qdrant | Local via Docker, or free-tier Cloud cluster | https://qdrant.tech |
| Generation API | API key (e.g. Groq for fast inference) | provider's console |
| Hugging Face | Account recommended (not strictly required — dataset is public) | https://huggingface.co |
| GitHub | Repo for submission | — |
| Deployment | Vercel/Netlify (frontend), Railway/Render/Fly.io (backend) | — |

### Local setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SARVAM_API_KEY, QDRANT_URL, GENERATION_API_KEY, etc.
docker run -p 6333:6333 qdrant/qdrant   # if running Qdrant locally
python scripts/ingest.py                # one-time: chunk + embed + index the dataset subset
uvicorn src.main:app --reload

# Frontend
cd frontend
npm install
cp .env.example .env    # set VITE_API_BASE_URL to the backend URL
npm run dev
```

### Running the latency benchmark

```bash
cd backend
python scripts/benchmark_latency.py --queries 50   # outputs P50/P70/P100 to a report file
```

## Latency Results (30 Multilingual Query Benchmark)

From offline latency evaluation ([backend/reports/latency_report.md](file:///d:/Hackathons/Hackkerhouse%20Goa%202026/Task%202%20By%20me/backend/reports/latency_report.md)) executing 30 diverse queries across Hindi (`hin`), Tamil (`tam`), and English (`en`):

| Pipeline Stage | P50 (ms) | P70 (ms) | P100 Max (ms) |
|---|:---:|:---:|:---:|
| **1. Query Embedding (`bge-m3`)** | 146.67 | 152.12 | 164.07 |
| **2. Dense Qdrant Vector Search (AWS Cloud)** | 280.85 | 281.69 | 290.47 |
| **3. Sparse BM25 Search (`rank_bm25`)** | 1.18 | 1.31 | 1.88 |
| **4. Reciprocal Rank Fusion (RRF)** | 0.02 | 0.02 | 0.04 |
| **5. Total Retrieval Sub-total** | 688.31 | 703.34 | 991.39 |
| **6. Retrieval Confidence Guardrail** | 0.00 | 0.01 | 0.01 |
| **7. Grounded LLM Generation** | 422.50 | 461.24 | 994.05 |
| **8. Grounding Guardrail Check** | 434.39 | 448.88 | 1025.42 |
| **9. Retrieval-to-Output (Target Metric)** | **1098.63** | **1126.47** | **1979.40** |
| **10. End-to-End Pipeline (Text)** | **2360.23** | **2444.70** | **3226.57** |

> **Telemetry Insights**:
> - Sparse BM25 ranking and Reciprocal Rank Fusion execute in **<1.5ms**, adding virtually zero latency overhead to dense vector retrieval.
> - Fast inference streaming yields sub-500ms time-to-first-token generation.
> - All stage percentiles computed using `numpy.percentile`.

## Dataset


`ai4bharat/MSMARCO-XI` — MS MARCO translated into ~13 Indic languages. Given the 55GB size and
the hackathon time budget, this build indexes a documented subset (see `process.md` for exact
languages/row counts used) rather than the full corpus.

## Guardrails

The system declines to answer when retrieval confidence is below threshold, flags off-topic
or unsafe input before it reaches retrieval, and runs a grounding check on generated answers
before returning them — see `context.md` for the full list.

## Team

`<names, roles>`

## Demo / submission links

- Live app: `<add>`
- Demo video: `<add>`
- Process video: `<add>`
