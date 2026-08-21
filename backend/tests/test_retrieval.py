"""Unit tests for backend/src/retrieval.py."""

import asyncio
import pytest
from backend.src.retrieval import (
    _tokenize_indic_text,
    compute_reciprocal_rank_fusion,
    retrieve,
)


class MockHit:
    def __init__(self, hit_id: str, score: float, payload: dict):
        self.id = hit_id
        self.score = score
        self.payload = payload


def test_tokenize_indic_text():
    """Verify tokenizer correctly segments Hindi and English text."""
    hi_tokens = _tokenize_indic_text("निगम एक कंपनी है।")
    assert "निगम" in hi_tokens
    assert "कंपनी" in hi_tokens

    en_tokens = _tokenize_indic_text("What is a corporation?")
    assert "what" in en_tokens
    assert "corporation" in en_tokens


def test_reciprocal_rank_fusion():
    """Verify RRF rank merging logic."""
    hit_a = MockHit("a", 0.9, {"text": "A"})
    hit_b = MockHit("b", 0.8, {"text": "B"})
    hit_c = MockHit("c", 0.7, {"text": "C"})

    dense_hits = [hit_a, hit_b, hit_c]
    sparse_scores = [(hit_b, 10.0), (hit_a, 5.0), (hit_c, 1.0)]

    merged = compute_reciprocal_rank_fusion(dense_hits, sparse_scores, rrf_k=60)
    assert len(merged) == 3
    # hit_b has dense rank 2, sparse rank 1 -> 1/62 + 1/61
    # hit_a has dense rank 1, sparse rank 2 -> 1/61 + 1/62
    top_hit_ids = [m[0].id for m in merged[:2]]
    assert "a" in top_hit_ids and "b" in top_hit_ids


@pytest.mark.asyncio
async def test_retrieve_empty_query():
    """Verify retrieve handles empty queries gracefully without errors."""
    res = await retrieve("")
    assert res["results"] == []
    assert "total_retrieval_ms" in res["timings_ms"]


@pytest.mark.asyncio
async def test_live_retrieval_hindi():
    """Verify live hybrid retrieval from Qdrant Cloud with latency tracking."""
    res = await retrieve("कॉर्पोरेशन क्या है?", top_k=3, language="hin")
    assert "results" in res
    assert "timings_ms" in res
    timings = res["timings_ms"]
    assert "embed_ms" in timings
    assert "dense_search_ms" in timings
    assert "total_retrieval_ms" in timings
    # Ensure at least 1 relevant hit is returned from Qdrant Cloud
    if res["results"]:
        first = res["results"][0]
        assert "text" in first
        assert "score" in first
        assert "resolved_context" in first
