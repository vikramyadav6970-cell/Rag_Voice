"""Integration and API unit tests for backend/src/main.py."""

import io
import pytest
from fastapi.testclient import TestClient
from backend.src.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /api/health returns 200 with healthy status and metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "voice-rag-backend"
    assert "timestamp" in data
    assert "version" in data


def test_ask_endpoint_empty_file_rejected():
    """Verify POST /api/ask rejects empty audio file with 400 Bad Request."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/ask",
        files={"file": ("empty.wav", empty_file, "audio/wav")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_ask_endpoint_unsupported_mime_rejected():
    """Verify POST /api/ask rejects non-audio file types with 415 Unsupported Media Type."""
    text_file = io.BytesIO(b"Hello text data")
    response = client.post(
        "/api/ask",
        files={"file": ("data.txt", text_file, "text/plain")},
    )
    assert response.status_code == 415
    assert "unsupported" in response.json()["detail"].lower()


def test_ask_text_endpoint_success():
    """Verify POST /api/ask/text executes complete RAG pipeline on text query."""
    response = client.post(
        "/api/ask/text",
        json={"query": "कॉर्पोरेशन क्या है?", "language": "hin", "top_k": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "timings_ms" in data
    assert "guardrail_flags" in data
    assert data["success"] is True
