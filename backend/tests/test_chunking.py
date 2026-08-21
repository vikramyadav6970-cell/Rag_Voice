"""Unit tests for backend/src/chunking.py multi-strategy chunking."""

import numpy as np
import pytest
from backend.src.chunking import (
    passage_native,
    fixed_size,
    semantic,
    hierarchical,
    chunk_document,
)

HINDI_SAMPLE_TEXT = (
    "निगम एक कंपनी या लोगों का समूह होता है जो एक एकल इकाई के रूप में कार्य करने के लिए अधिकृत होता है। "
    "एक कंपनी एक विशिष्ट देश में निगमित होती है, अक्सर उस देश के एक छोटे उपसमूह की सीमाओं के भीतर। "
    "निगम तब उस राज्य में निगमन के कानूनों द्वारा शासित होता है।"
)

ENGLISH_SAMPLE_TEXT = (
    "A corporation is an organization—usually a group of people or a company—authorized by the state to act as a single entity. "
    "Early incorporated entities were established by charter (i.e. by an ad hoc act granted by a monarch or passed by a parliament). "
    "Most jurisdictions now allow the creation of new corporations through registration."
)


def test_passage_native_structure():
    """Verify passage_native returns a single, well-formed chunk dict."""
    chunks = passage_native(
        text=HINDI_SAMPLE_TEXT,
        source_doc_id="doc_101",
        language="hin",
        metadata={"query_id": "q_1"},
    )
    assert len(chunks) == 1
    c = chunks[0]
    assert c["text"] == HINDI_SAMPLE_TEXT
    assert c["source_doc_id"] == "doc_101"
    assert c["language"] == "hin"
    assert c["strategy"] == "passage_native"
    assert "chunk_id" in c and len(c["chunk_id"]) == 16
    assert c["metadata"]["parent_id"] is None
    assert c["metadata"]["query_id"] == "q_1"


def test_fixed_size_chunking():
    """Verify fixed_size produces multiple overlapping chunks and preserves metadata."""
    chunks = fixed_size(
        text=ENGLISH_SAMPLE_TEXT,
        source_doc_id="doc_102",
        size_tokens=25,
        overlap_tokens=8,
        language="en",
    )
    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert c["strategy"] == "fixed_size"
        assert c["source_doc_id"] == "doc_102"
        assert c["metadata"]["window_index"] == idx
        assert c["metadata"]["token_count"] > 0
        assert len(c["chunk_id"]) == 16


def test_semantic_chunking_fallback():
    """Verify semantic chunking splits at sentences when no model is provided."""
    chunks = semantic(
        text=HINDI_SAMPLE_TEXT,
        source_doc_id="doc_103",
        embedding_model=None,
        threshold=0.65,
        language="hin",
    )
    assert len(chunks) >= 1
    for c in chunks:
        assert c["strategy"] == "semantic"
        assert c["language"] == "hin"
        assert "chunk_id" in c


def test_semantic_chunking_with_mock_model():
    """Verify semantic chunking properly partitions when embeddings trigger a threshold drop."""
    # Create mock encoder that returns orthogonal vectors on sentence 2 vs sentence 1
    class MockEmbeddingModel:
        def encode(self, texts, **kwargs):
            vecs = []
            for i, _ in enumerate(texts):
                # Orthogonal vector for each sentence
                v = np.zeros(8, dtype=np.float32)
                v[i % 8] = 1.0
                vecs.append(v)
            return np.array(vecs)

    mock_model = MockEmbeddingModel()
    chunks = semantic(
        text=HINDI_SAMPLE_TEXT,
        source_doc_id="doc_103_mock",
        embedding_model=mock_model,
        threshold=0.5,
        language="hin",
    )
    # Since orthogonal vectors have 0.0 cosine similarity (< 0.5), each sentence becomes its own chunk
    assert len(chunks) >= 2
    for c in chunks:
        assert c["strategy"] == "semantic"
        assert "semantic_index" in c["metadata"]


def test_hierarchical_chunking():
    """Verify hierarchical chunking produces 1 parent and >= 1 child linked via parent_id."""
    chunks = hierarchical(
        text=HINDI_SAMPLE_TEXT,
        source_doc_id="doc_104",
        child_size_tokens=15,
        child_overlap_tokens=5,
        language="hin",
    )
    assert len(chunks) >= 2
    parent = chunks[0]
    assert parent["strategy"] == "hierarchical_parent"
    assert parent["metadata"]["is_parent"] is True
    assert parent["metadata"]["parent_id"] is None

    children = chunks[1:]
    for idx, child in enumerate(children):
        assert child["strategy"] == "hierarchical_child"
        assert child["metadata"]["is_parent"] is False
        assert child["metadata"]["parent_id"] == parent["chunk_id"]
        assert child["metadata"]["child_index"] == idx


def test_chunk_document_unified_router():
    """Verify chunk_document routes correctly to all strategies."""
    for strat in ["passage_native", "fixed_size", "semantic", "hierarchical"]:
        res = chunk_document(
            text=HINDI_SAMPLE_TEXT,
            strategy=strat,
            source_doc_id="doc_test",
            language="hin",
        )
        assert len(res) >= 1
        assert "chunk_id" in res[0]
