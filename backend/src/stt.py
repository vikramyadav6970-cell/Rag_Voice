"""Speech-to-Text (STT) Client — Sarvam AI (Saaras v3) Integration.

Handles streaming & batch audio transcription for Indic and code-mixed utterances,
with timeout bounds, tenacity retry policies, and graceful error degradation.
"""

from __future__ import annotations

import io
import os
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SARVAM_STT_ENDPOINT = "https://api.sarvam.ai/speech-to-text"
DEFAULT_MODEL = "saaras:v3"

# Map 2/3-letter language hints to Sarvam BCP-47 language codes
LANGUAGE_CODE_MAP = {
    "hi": "hi-IN",
    "hin": "hi-IN",
    "ta": "ta-IN",
    "tam": "ta-IN",
    "te": "te-IN",
    "tel": "te-IN",
    "bn": "bn-IN",
    "ben": "bn-IN",
    "mr": "mr-IN",
    "mar": "mr-IN",
    "gu": "gu-IN",
    "guj": "gu-IN",
    "kn": "kn-IN",
    "kan": "kn-IN",
    "ml": "ml-IN",
    "mal": "ml-IN",
    "pa": "pa-IN",
    "pan": "pa-IN",
    "od": "od-IN",
    "ori": "od-IN",
    "en": "en-IN",
    "eng": "en-IN",
}


def _get_sarvam_api_key() -> str:
    """Retrieve SARVAM_API_KEY from environment."""
    key = os.getenv("SARVAM_API_KEY")
    if not key:
        raise ValueError("SARVAM_API_KEY is not configured in backend/.env")
    return key.strip()


def normalize_language_code(lang: Optional[str]) -> str:
    """Map language hint to standard Sarvam language_code (e.g. 'hi' -> 'hi-IN')."""
    if not lang:
        return "unknown"
    clean = lang.strip().lower()
    return LANGUAGE_CODE_MAP.get(clean, clean if "-" in clean else "unknown")


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
    reraise=True,
)
async def _call_sarvam_stt_api(
    audio_bytes: bytes,
    language_code: str,
    model: str,
    api_key: str,
    filename: str = "audio.wav",
    content_type: Optional[str] = None,
    timeout_sec: float = 5.0,
) -> Dict[str, Any]:
    """Execute raw HTTP POST to Sarvam STT REST API with network retry."""
    headers = {
        "api-subscription-key": api_key,
    }

    # Detect appropriate audio MIME type
    if not content_type:
        if filename.endswith(".webm"):
            content_type = "audio/webm"
        elif filename.endswith(".ogg") or filename.endswith(".opus"):
            content_type = "audio/ogg"
        elif filename.endswith(".mp3"):
            content_type = "audio/mpeg"
        else:
            content_type = "audio/wav"

    files = {
        "file": (filename, audio_bytes, content_type),
    }

    data: Dict[str, Any] = {
        "model": model,
        "with_diarization": "false",
    }

    if language_code and language_code != "unknown":
        data["language_code"] = language_code

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        response = await client.post(
            SARVAM_STT_ENDPOINT,
            headers=headers,
            files=files,
            data=data,
        )
        response.raise_for_status()
        return response.json()


async def transcribe(
    audio_bytes: bytes,
    language_hint: Optional[str] = None,
    filename: str = "audio.wav",
    timeout_sec: float = 5.0,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Transcribe an audio utterance using Sarvam AI STT API.

    Args:
        audio_bytes: Raw bytes of the audio file (WAV / MP3 / OGG / WebM).
        language_hint: Optional language code hint (e.g. 'hin', 'hi', 'tam', 'ta').
        filename: Optional filename label.
        timeout_sec: Maximum timeout in seconds (default: 5.0s).
        model: Sarvam STT model name (default: 'saaras:v3').

    Returns:
        Dict with fields:
        {
            "text": str,
            "detected_language": str | None,
            "latency_ms": float,
            "success": bool,
            "error": str | None,
        }
    """
    t_start = time.perf_counter()

    if not audio_bytes or len(audio_bytes) == 0:
        return {
            "text": "",
            "detected_language": None,
            "latency_ms": 0.0,
            "success": False,
            "error": "Empty audio payload provided.",
        }

    try:
        api_key = _get_sarvam_api_key()
    except ValueError as e:
        latency = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "text": "",
            "detected_language": None,
            "latency_ms": latency,
            "success": False,
            "error": str(e),
        }

    lang_code = normalize_language_code(language_hint)
    print(f"[STT] Calling Sarvam Saaras v3: lang_code='{lang_code}', filename='{filename}', size={len(audio_bytes):,} bytes")

    try:
        raw_res = await _call_sarvam_stt_api(
            audio_bytes=audio_bytes,
            language_code=lang_code,
            model=model,
            api_key=api_key,
            filename=filename,
            timeout_sec=timeout_sec,
        )

        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        transcript = raw_res.get("transcript", "").strip()
        detected_lang = raw_res.get("language_code") or language_hint
        print(f"[STT] Sarvam Result: transcript='{transcript}', detected_lang='{detected_lang}', latency={latency_ms}ms")

        return {
            "text": transcript,
            "detected_language": detected_lang,
            "latency_ms": latency_ms,
            "success": True,
            "error": None,
            "raw_response": raw_res,
        }

    except httpx.HTTPStatusError as http_err:
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        print(f"[STT] Sarvam HTTP Status Error: {http_err.response.status_code} - {http_err.response.text}")

        status = http_err.response.status_code
        err_body = http_err.response.text
        return {
            "text": "",
            "detected_language": None,
            "latency_ms": latency_ms,
            "success": False,
            "error": f"Sarvam API HTTP {status}: {err_body}",
        }

    except Exception as exc:
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "text": "",
            "detected_language": None,
            "latency_ms": latency_ms,
            "success": False,
            "error": f"Sarvam STT failed: {str(exc)}",
        }
