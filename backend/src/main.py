"""FastAPI Application Entrypoint — Voice-Enabled Indic RAG API.

Provides endpoints for audio question transcription (/api/ask),
health diagnostics (/api/health), and CORS-enabled frontend communication.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.stt import transcribe

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Constants for audio validation
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
    "application/octet-stream",  # Fallback from some browser media recorders
}

# --- Pydantic Schema Models ---

class HealthResponse(BaseModel):
    """Health check diagnostic response."""
    status: str = Field(default="healthy", description="Service health state")
    service: str = Field(default="voice-rag-backend", description="Microservice name")
    timestamp: float = Field(default_factory=time.time, description="Current epoch timestamp")
    version: str = Field(default="0.1.0", description="API version")


class AskAudioResponse(BaseModel):
    """Response payload for audio question submission."""
    transcript: str = Field(default="", description="Transcribed query text")
    detected_language: Optional[str] = Field(default=None, description="Detected or normalized language code")
    stt_latency_ms: float = Field(default=0.0, description="Sarvam STT execution time in milliseconds")
    success: bool = Field(default=True, description="Whether transcription succeeded")
    error: Optional[str] = Field(default=None, description="Error message if transcription failed")

    # Placeholders for Phase 3 end-to-end RAG pipeline
    answer: Optional[str] = Field(default=None, description="Grounded LLM response (Phase 3)")
    context_chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved evidence chunks")
    retrieval_latency_ms: Optional[float] = Field(default=None, description="Retrieval latency in ms")
    generation_latency_ms: Optional[float] = Field(default=None, description="Generation latency in ms")
    total_latency_ms: Optional[float] = Field(default=None, description="End-to-end processing latency in ms")


# --- FastAPI Application Setup ---

app = FastAPI(
    title="Indic Voice-Enabled RAG API",
    description="Multilingual Voice RAG Service for HH Goa 2026",
    version="0.1.0",
)

# Configure CORS for Vite React Frontend
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000,http://localhost:5173")
allowed_origins = [orig.strip() for orig in frontend_origin_env.split(",") if orig.strip()]
if "*" not in allowed_origins:
    allowed_origins.append("*")  # Permissive fallback during development

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


@app.post("/api/ask", response_model=AskAudioResponse, tags=["Voice RAG"])
async def ask_voice_query(
    file: UploadFile = File(..., description="Recorded audio file (WAV/MP3/WebM/OGG)"),
    language_hint: Optional[str] = Form(None, description="Optional language hint (e.g. 'hin', 'tam', 'hi-IN')"),
) -> AskAudioResponse:
    """Accept voice recording, transcribe with Sarvam AI, and return transcript with latency.

    Full retrieval and LLM answer generation is linked in Phase 3.
    """
    t_start = time.perf_counter()

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

    # 3. Transcribe with Sarvam AI STT
    stt_res = await transcribe(
        audio_bytes=audio_bytes,
        language_hint=language_hint,
        filename=filename,
    )

    total_latency = round((time.perf_counter() - t_start) * 1000, 2)

    return AskAudioResponse(
        transcript=stt_res.get("text", ""),
        detected_language=stt_res.get("detected_language"),
        stt_latency_ms=stt_res.get("latency_ms", 0.0),
        success=stt_res.get("success", False),
        error=stt_res.get("error"),
        total_latency_ms=total_latency,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
