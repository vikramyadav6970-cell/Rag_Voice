"""Unit tests for backend/src/stt.py."""

import pytest
from backend.src.stt import normalize_language_code, transcribe


def test_normalize_language_code():
    """Verify mapping of 2/3 letter codes to Sarvam BCP-47 codes."""
    assert normalize_language_code("hin") == "hi-IN"
    assert normalize_language_code("hi") == "hi-IN"
    assert normalize_language_code("tam") == "ta-IN"
    assert normalize_language_code("ta") == "ta-IN"
    assert normalize_language_code("tel") == "te-IN"
    assert normalize_language_code("ben") == "bn-IN"
    assert normalize_language_code(None) == "unknown"


@pytest.mark.asyncio
async def test_transcribe_empty_bytes():
    """Verify transcribe handles empty audio gracefully without raising exceptions."""
    res = await transcribe(b"")
    assert res["success"] is False
    assert res["text"] == ""
    assert "Empty audio" in res["error"]
