"""Chunking Strategies Module — Multi-Strategy Chunking for Indic & Multilingual RAG.

Architectural Strategy Comparison & Trade-off Analysis:
-------------------------------------------------------
1. PASSAGE_NATIVE (Baseline):
   - Mechanism: Treats each MSMARCO passage as an atomic, standalone chunk without modification.
   - Precision vs. Context: Moderate-high context completeness; relies on dataset-native passage
     boundaries. Preserves human-annotated / machine-translated semantic cohesion.
   - Compute & Cost: O(1) compute, zero chunking latency, single embedding per passage.
   - When it Wins: General factoid Q&A where queries map directly to single paragraph answers.

2. FIXED_SIZE (Token-based Sliding Window with Overlap):
   - Mechanism: Slices text into uniform token windows (e.g. 100-140 tokens) with configurable
     overlap (e.g. 20-30 tokens).
   - Precision vs. Context: Predictable context size for vector DB indices. Overlap guarantees that
     information straddling window boundaries is not lost.
   - Compute & Cost: O(N) linear text pass, near-instantaneous tokenization.
   - When it Wins: Homogeneous indexing across varying document lengths, preventing vector DB
     token bloat and payload imbalance.
   - Indic Tokenizer Rationale: Indic scripts (Devanagari, Tamil, etc.) use conjunct consonants
     (aksharas) and combining matras. Arbitrary character/byte slicing corrupts Unicode glyphs.
     We use word-boundary preservation combined with tiktoken cl100k_base token tracking to ensure
     linguistic validity and bounded token counts.

3. SEMANTIC (Sentence Cosine Boundary Segmentation):
   - Mechanism: Decomposes text into sentence units using Indic sentence boundaries ('।', '?', '!',
     '.', '\n'), computes embeddings for adjacent sentences, and places a chunk cut whenever cosine
     similarity between consecutive sentence embeddings drops below a threshold (e.g. 0.65).
   - Precision vs. Context: High semantic purity. Chunks expand or contract based on thematic shifts
     rather than arbitrary token counts.
   - Compute & Cost: O(M) embeddings computed per M sentences during ingestion.
   - When it Wins: Multi-topic passages or compound explanations where separating distinct ideas
     prevents cross-topic vector dilution.

4. HIERARCHICAL (Parent-Child Multi-Scale Representation):
   - Mechanism: Generates granular "child" chunks (40-60 tokens) for dense vector search precision,
     linked via `parent_id` to the encompassing "parent" chunk (150-300 tokens) for generation context.
   - Precision vs. Context: Resolves the classic RAG tradeoff — retrieval benefits from small, tight
     vectors, while LLM synthesis benefits from expansive, coherent context.
   - Compute & Cost: Requires indexing child chunks in vector DB with parent payloads or references.
   - When it Wins: Dense, nuanced queries where keyword/semantic matching requires pinpoint accuracy
     but LLM reasoning requires full situational context.

Coding Conventions Adherence:
- Production-grade implementation with full type annotations.
- Deterministic chunk_id generation for idempotency.
- Explicit error handling and fallback mechanisms.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Callable, Dict, List, Optional, Sequence
import numpy as np

try:
    import tiktoken
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODER = None


# Sentence delimiter regex supporting Indic danda ('।'), double danda ('॥'), English punctuation, and newlines
_SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[।॥.!?\n])\s+")


def _generate_chunk_id(
    source_doc_id: str,
    strategy: str,
    index: int,
    text: str,
) -> str:
    """Generate a deterministic 16-character hex ID for a chunk."""
    seed = f"{source_doc_id}::{strategy}::{index}::{text.strip()[:48]}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _count_tokens(text: str) -> int:
    """Estimate or accurately count token length using tiktoken with whitespace fallback."""
    if _TIKTOKEN_ENCODER is not None:
        try:
            return len(_TIKTOKEN_ENCODER.encode(text))
        except Exception:
            pass
    # Fallback heuristic for Indic/multilingual text: ~1.3 tokens per whitespace-separated word
    words = text.split()
    return max(1, int(len(words) * 1.3))


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentence units respecting Indic and standard punctuation."""
    cleaned = text.strip()
    if not cleaned:
        return []
    parts = _SENTENCE_SPLIT_REGEX.split(cleaned)
    sentences = [p.strip() for p in parts if p.strip()]
    return sentences if sentences else [cleaned]


def passage_native(
    text: str,
    source_doc_id: str,
    language: str = "hin",
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Chunking Strategy 1: Passage Native (Baseline).

    Treats the passage as a single, atomic chunk without subdivision.

    Args:
        text: Passage text content.
        source_doc_id: Identifier of the source document/passage.
        language: Language code (e.g. 'hin', 'tam', 'ben').
        metadata: Optional dictionary of additional metadata.

    Returns:
        List containing a single chunk dictionary.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    strategy = "passage_native"
    chunk_id = _generate_chunk_id(source_doc_id, strategy, 0, clean_text)
    meta = dict(metadata or {})
    meta.update({
        "language": language,
        "source_doc_id": source_doc_id,
        "strategy": strategy,
        "parent_id": None,
        "token_count": _count_tokens(clean_text),
        "char_count": len(clean_text),
    })

    return [{
        "text": clean_text,
        "chunk_id": chunk_id,
        "source_doc_id": source_doc_id,
        "language": language,
        "strategy": strategy,
        "metadata": meta,
    }]


def fixed_size(
    text: str,
    source_doc_id: str,
    size_tokens: int = 120,
    overlap_tokens: int = 25,
    language: str = "hin",
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Chunking Strategy 2: Fixed-Size Token Window with Overlap.

    Slices text into sliding windows of approximately `size_tokens` with `overlap_tokens`.
    Word boundaries are strictly preserved to avoid corrupting Indic Unicode aksharas.

    Args:
        text: Input text content.
        source_doc_id: Source document identifier.
        size_tokens: Target token count per chunk.
        overlap_tokens: Token overlap between successive chunks.
        language: Language code (e.g. 'hin', 'tam').
        metadata: Optional metadata dict.

    Returns:
        List of chunk dictionaries.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    words = clean_text.split()
    if not words:
        return []

    # Map target token bounds to word count heuristic
    # Indic words average ~1.3-1.6 subword tokens
    target_words = max(5, int(size_tokens / 1.3))
    overlap_words = max(1, int(overlap_tokens / 1.3))
    if overlap_words >= target_words:
        overlap_words = target_words // 2

    step = target_words - overlap_words
    chunks: List[Dict[str, Any]] = []
    strategy = "fixed_size"

    idx = 0
    start = 0
    n_words = len(words)

    while start < n_words:
        end = min(start + target_words, n_words)
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words).strip()

        if chunk_text:
            chunk_id = _generate_chunk_id(source_doc_id, strategy, idx, chunk_text)
            meta = dict(metadata or {})
            meta.update({
                "language": language,
                "source_doc_id": source_doc_id,
                "strategy": strategy,
                "parent_id": None,
                "window_index": idx,
                "token_count": _count_tokens(chunk_text),
                "char_count": len(chunk_text),
            })

            chunks.append({
                "text": chunk_text,
                "chunk_id": chunk_id,
                "source_doc_id": source_doc_id,
                "language": language,
                "strategy": strategy,
                "metadata": meta,
            })
            idx += 1

        if end >= n_words:
            break
        start += step

    return chunks


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two 1D numpy vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def semantic(
    text: str,
    source_doc_id: str,
    embedding_model: Any = None,
    threshold: float = 0.65,
    language: str = "hin",
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Chunking Strategy 3: Semantic Sentence Boundary Chunking.

    Splits text into sentences, computes sentence embeddings, and partitions into new chunks
    whenever cosine similarity between consecutive sentences drops below `threshold`.

    Args:
        text: Text to chunk.
        source_doc_id: Source document ID.
        embedding_model: Optional SentenceTransformer or callable `model.encode(texts)`.
            If None or model fails, falls back to structural sentence aggregation.
        threshold: Cosine similarity threshold for segmenting (0.0 to 1.0, default 0.65).
        language: Language code.
        metadata: Optional metadata dict.

    Returns:
        List of chunk dictionaries.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    sentences = _split_into_sentences(clean_text)
    if len(sentences) <= 1:
        return passage_native(clean_text, source_doc_id, language, metadata)

    strategy = "semantic"
    grouped_chunks: List[str] = []

    # If embedding model is provided, compute semantic similarity cuts
    embeddings: Optional[List[np.ndarray]] = None
    if embedding_model is not None:
        try:
            if hasattr(embedding_model, "encode"):
                raw_embeds = embedding_model.encode(sentences, convert_to_numpy=True)
                embeddings = [np.array(e, dtype=np.float32) for e in raw_embeds]
            elif callable(embedding_model):
                raw_embeds = embedding_model(sentences)
                embeddings = [np.array(e, dtype=np.float32) for e in raw_embeds]
        except Exception:
            embeddings = None

    if embeddings is not None and len(embeddings) == len(sentences):
        current_sentences = [sentences[0]]
        for i in range(1, len(sentences)):
            sim = _cosine_similarity(embeddings[i - 1], embeddings[i])
            if sim < threshold:
                # Semantic boundary detected — close current chunk and begin new one
                grouped_chunks.append(" ".join(current_sentences).strip())
                current_sentences = [sentences[i]]
            else:
                current_sentences.append(sentences[i])
        if current_sentences:
            grouped_chunks.append(" ".join(current_sentences).strip())
    else:
        # Fallback: Group sentences into multi-sentence units (~2-3 sentences each)
        batch_size = 2
        for i in range(0, len(sentences), batch_size):
            grouped_chunks.append(" ".join(sentences[i:i + batch_size]).strip())

    chunks: List[Dict[str, Any]] = []
    for idx, c_text in enumerate(grouped_chunks):
        if not c_text:
            continue
        chunk_id = _generate_chunk_id(source_doc_id, strategy, idx, c_text)
        meta = dict(metadata or {})
        meta.update({
            "language": language,
            "source_doc_id": source_doc_id,
            "strategy": strategy,
            "parent_id": None,
            "semantic_index": idx,
            "token_count": _count_tokens(c_text),
            "char_count": len(c_text),
        })

        chunks.append({
            "text": c_text,
            "chunk_id": chunk_id,
            "source_doc_id": source_doc_id,
            "language": language,
            "strategy": strategy,
            "metadata": meta,
        })

    return chunks if chunks else passage_native(clean_text, source_doc_id, language, metadata)


def hierarchical(
    text: str,
    source_doc_id: str,
    child_size_tokens: int = 60,
    child_overlap_tokens: int = 15,
    language: str = "hin",
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Chunking Strategy 4: Hierarchical Parent-Child Chunking.

    Produces a primary parent chunk (the comprehensive passage) and multiple granular
    child chunks (for fine-grained vector retrieval), with `parent_id` linking child to parent.

    Args:
        text: Input text content.
        source_doc_id: Source document ID.
        child_size_tokens: Target token size for child chunks (default: 60).
        child_overlap_tokens: Overlap between consecutive child chunks (default: 15).
        language: Language code.
        metadata: Optional metadata dictionary.

    Returns:
        List containing the parent chunk dictionary followed by all child chunk dictionaries.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    parent_strategy = "hierarchical_parent"
    child_strategy = "hierarchical_child"

    # 1. Construct parent chunk
    parent_id = _generate_chunk_id(source_doc_id, parent_strategy, 0, clean_text)
    parent_meta = dict(metadata or {})
    parent_meta.update({
        "language": language,
        "source_doc_id": source_doc_id,
        "strategy": parent_strategy,
        "parent_id": None,
        "is_parent": True,
        "token_count": _count_tokens(clean_text),
        "char_count": len(clean_text),
    })

    parent_chunk: Dict[str, Any] = {
        "text": clean_text,
        "chunk_id": parent_id,
        "source_doc_id": source_doc_id,
        "language": language,
        "strategy": parent_strategy,
        "metadata": parent_meta,
    }

    # 2. Construct child chunks
    child_chunks_raw = fixed_size(
        text=clean_text,
        source_doc_id=source_doc_id,
        size_tokens=child_size_tokens,
        overlap_tokens=child_overlap_tokens,
        language=language,
        metadata=metadata,
    )

    child_chunks: List[Dict[str, Any]] = []
    for idx, c in enumerate(child_chunks_raw):
        c_text = c["text"]
        child_id = _generate_chunk_id(source_doc_id, child_strategy, idx, c_text)
        c_meta = dict(c["metadata"])
        c_meta.update({
            "strategy": child_strategy,
            "parent_id": parent_id,
            "is_parent": False,
            "child_index": idx,
        })

        child_chunks.append({
            "text": c_text,
            "chunk_id": child_id,
            "source_doc_id": source_doc_id,
            "language": language,
            "strategy": child_strategy,
            "metadata": c_meta,
        })

    # Return parent chunk first, followed by child chunks
    return [parent_chunk] + child_chunks


def chunk_document(
    text: str,
    strategy: str = "passage_native",
    source_doc_id: str = "doc_0",
    language: str = "hin",
    embedding_model: Any = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Unified chunking interface supporting all 4 chunking strategies.

    Args:
        text: Input text content.
        strategy: One of 'passage_native', 'fixed_size', 'semantic', 'hierarchical'.
        source_doc_id: Source document ID.
        language: Language code.
        embedding_model: Optional embedding model for semantic chunking.
        metadata: Optional metadata dictionary.
        **kwargs: Additional parameters passed to specific chunkers.

    Returns:
        List of chunk dictionaries.
    """
    clean_strategy = strategy.strip().lower()

    if clean_strategy in ("passage_native", "native", "baseline"):
        return passage_native(text, source_doc_id, language, metadata)

    elif clean_strategy in ("fixed_size", "fixed", "sliding_window"):
        size_tokens = kwargs.get("size_tokens", 120)
        overlap_tokens = kwargs.get("overlap_tokens", 25)
        return fixed_size(
            text,
            source_doc_id,
            size_tokens=size_tokens,
            overlap_tokens=overlap_tokens,
            language=language,
            metadata=metadata,
        )

    elif clean_strategy in ("semantic", "sentence_similarity"):
        threshold = kwargs.get("threshold", 0.65)
        return semantic(
            text,
            source_doc_id,
            embedding_model=embedding_model,
            threshold=threshold,
            language=language,
            metadata=metadata,
        )

    elif clean_strategy in ("hierarchical", "parent_child"):
        child_size_tokens = kwargs.get("child_size_tokens", 60)
        child_overlap_tokens = kwargs.get("child_overlap_tokens", 15)
        return hierarchical(
            text,
            source_doc_id,
            child_size_tokens=child_size_tokens,
            child_overlap_tokens=child_overlap_tokens,
            language=language,
            metadata=metadata,
        )

    else:
        # Fallback to passage_native with a warning in metadata
        meta = dict(metadata or {})
        meta["unknown_strategy_requested"] = strategy
        return passage_native(text, source_doc_id, language, meta)
