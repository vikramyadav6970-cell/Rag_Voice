"""Unit tests for backend/src/generation.py."""

import pytest
from backend.src.generation import (
    REFUSAL_PHRASE_EN,
    format_context_for_prompt,
    generate,
)


def test_format_context_for_prompt():
    """Verify formatting of retrieved chunks with metadata into prompt."""
    chunks = [
        {"text": "निगम एक कंपनी है।", "source_doc_id": "doc_1", "strategy": "passage_native", "score": 0.85},
        {"text": "यह कानूनी इकाई है।", "resolved_context": "यह एक कानूनी इकाई है।", "source_doc_id": "doc_2", "strategy": "hierarchical_child"},
    ]
    formatted = format_context_for_prompt(chunks)
    assert "Passage 1" in formatted
    assert "निगम एक कंपनी है" in formatted
    assert "यह एक कानूनी इकाई है" in formatted


@pytest.mark.asyncio
async def test_generate_empty_context_refusal():
    """Verify system explicitly returns refusal when no context chunks are supplied."""
    res = await generate(query="What is a corporation?", context_chunks=[])
    assert res["success"] is True
    assert REFUSAL_PHRASE_EN in res["answer"]
    assert res["is_grounded"] is True


@pytest.mark.asyncio
async def test_generate_with_context():
    """Verify generation returns answer and latency when context is provided."""
    sample_context = [
        {"text": "A corporation is a company authorized to act as a single entity in law.", "source_doc_id": "1102432_p1", "strategy": "passage_native"}
    ]
    res = await generate(query="What is a corporation?", context_chunks=sample_context)
    assert res["success"] is True
    assert len(res["answer"]) > 0
    assert "latency_ms" in res
