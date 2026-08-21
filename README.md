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
- **Embeddings**: bge-m3 (multilingual)
- **Vector DB**: Qdrant
- **Generation**: `<fill in provider/model once chosen>`
- **Harness**: LangGraph
- **Backend**: FastAPI (Python)
- **Frontend**: React (Vite)
- **Deployment**: `<backend host>` / `<frontend host>`

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

## Latency Target & Measurement Methodology

To meet the requirement while accounting for external LLM API physics:
- **Retrieval Pipeline (Target: < 200ms)**: Query embedding (`bge-m3`) → Vector DB search (`Qdrant`) → Context assembly & input guardrails. We benchmark and enforce **P50 / P70 / P100 under 200ms**.
- **Generation Pipeline (Reported Separately)**: LLM streaming time-to-first-token (TTFT) and total generation time are metered, logged, and reported separately with per-stage breakdowns.
- **End-to-End Analytics**: The benchmark suite outputs detailed stage-by-stage timings (STT → Embed → Vector Search → Context Assembly → LLM TTFT → LLM End).


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
