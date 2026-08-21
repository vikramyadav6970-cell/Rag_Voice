"""FastAPI Application Entrypoint — Voice & Text Indic RAG API.

Provides endpoints for audio question submission (/api/ask),
direct text query evaluation (/api/ask/text), and system health diagnostics (/api/health).
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure standard UTF-8 stream encoding across Windows and Linux environments
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.harness import run_rag_pipeline

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit for voice Q&A
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
    "audio/aac",
    "audio/m4a",
    "audio/x-m4a",
    "application/octet-stream",
}

# --- Pydantic Schema Models ---

class HealthResponse(BaseModel):
    """Health check diagnostic response."""
    status: str = Field(default="healthy", description="Service health state")
    service: str = Field(default="voice-rag-backend", description="Microservice name")
    timestamp: float = Field(default_factory=time.time, description="Current epoch timestamp")
    version: str = Field(default="0.1.0", description="API version")


class AskTextRequest(BaseModel):
    """Direct text question request payload."""
    query: str = Field(..., description="User question in natural language (Hindi/Tamil/English)")
    language: Optional[str] = Field(default=None, description="Optional language filter (e.g. 'hin', 'tam')")
    strategy: Optional[str] = Field(default=None, description="Optional chunking strategy override")
    top_k: int = Field(default=4, description="Number of context passages to retrieve")


class SourceCitation(BaseModel):
    """Source passage evidence citation."""
    chunk_id: Optional[str] = None
    source_doc_id: Optional[str] = None
    strategy: Optional[str] = None
    score: Optional[float] = None
    text: Optional[str] = None
    resolved_context: Optional[str] = None
    language: Optional[str] = None


class RAGResponse(BaseModel):
    """Unified full-pipeline RAG response."""
    transcript: str = Field(default="", description="Transcribed audio or user query")
    query: str = Field(default="", description="Cleaned question processed by retrieval")
    answer: str = Field(default="", description="Synthesized grounded answer from LLM")
    sources: List[SourceCitation] = Field(default_factory=list, description="Retrieved evidence chunks")
    timings_ms: Dict[str, float] = Field(default_factory=dict, description="Per-stage latency telemetry")
    guardrail_flags: Dict[str, Any] = Field(default_factory=dict, description="Safety and grounding validation flags")
    detected_language: Optional[str] = Field(default=None, description="Detected or specified language")
    success: bool = Field(default=True, description="Overall pipeline success status")
    errors: Dict[str, str] = Field(default_factory=dict, description="Per-stage error or warning details")


# --- FastAPI Application Setup ---

app = FastAPI(
    title="Indic Voice-Enabled RAG API",
    description="Multilingual Voice RAG Service for HH Goa 2026 (STT -> Retrieve -> Generate -> Guardrails)",
    version="0.1.0",
)

# Configure CORS for Vite React Frontend
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000,http://localhost:5173")
allowed_origins = [orig.strip() for orig in frontend_origin_env.split(",") if orig.strip()]
if "*" not in allowed_origins:
    allowed_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["Diagnostics"])
async def health_check() -> HealthResponse:
    """Check backend operational health and readiness."""
    return HealthResponse()


@app.post("/api/ask", response_model=RAGResponse, tags=["Voice RAG"])
async def ask_voice_query(
    file: UploadFile = File(..., description="Recorded audio file (WAV/MP3/WebM/OGG)"),
    language_hint: Optional[str] = Form(None, description="Optional language hint (e.g. 'hin', 'tam', 'hi-IN')"),
    strategy: Optional[str] = Form(None, description="Optional chunking strategy filter"),
) -> RAGResponse:
    """Accept voice recording, transcribe with Sarvam AI, retrieve grounded context, and synthesize answer."""
    # 1. Validate MIME type
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    filename = file.filename or "recording.wav"
    file_ext = os.path.splitext(filename)[1].lower()

    if content_type and content_type not in ALLOWED_AUDIO_MIME_TYPES and file_ext not in [".wav", ".mp3", ".ogg", ".webm", ".m4a", ".flac"]:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio media type '{content_type}'. Supported: WAV, MP3, WebM, OGG, M4A.",
        )

    # 2. Read and validate payload size
    try:
        audio_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded audio file: {str(exc)}",
        )

    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio size ({len(audio_bytes):,} bytes) exceeds maximum limit of 10MB.",
        )

    print(f"\n[API /api/ask] Received voice upload: filename='{filename}', content_type='{content_type}', size={len(audio_bytes):,} bytes, language_hint='{language_hint}'")

    # Diagnostic: save uploaded audio payload to inspect container headers
    try:
        debug_audio_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "last_uploaded.webm"))
        with open(debug_audio_path, "wb") as f:
            f.write(audio_bytes)
        print(f"[API /api/ask] Saved uploaded audio to {debug_audio_path}")
    except Exception as e:
        print(f"[API /api/ask] Failed to save debug audio: {e}")

    # 3. Execute End-to-End Voice RAG Pipeline

    pipeline_result = await run_rag_pipeline(
        audio_bytes=audio_bytes,
        audio_filename=filename,
        language_hint=language_hint,
        strategy=strategy,
    )

    try:
        ans_preview = repr(pipeline_result.get('answer', ''))[:80]
        print(f"[API /api/ask] Pipeline Result: transcript='{pipeline_result.get('transcript')}', query='{pipeline_result.get('query')}', answer={ans_preview}, flags={pipeline_result.get('guardrail_flags')}, sources={len(pipeline_result.get('sources', []))}")
    except Exception:
        pass

    return RAGResponse(**pipeline_result)





@app.post("/api/ask/text", response_model=RAGResponse, tags=["Text RAG"])
async def ask_text_query(request: AskTextRequest) -> RAGResponse:
    """Execute grounded RAG pipeline directly from text query without STT step."""
    clean_q = request.query.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    pipeline_result = await run_rag_pipeline(
        query=clean_q,
        language_hint=request.language,
        strategy=request.strategy,
        top_k=request.top_k,
    )

    return RAGResponse(**pipeline_result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
