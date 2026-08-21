"""Retrieval Service — Multilingual Hybrid Retrieval & Chunk Strategy Resolution.

Implements sub-200ms hybrid search (Dense Vector + Sparse BM25 + Reciprocal Rank Fusion),
hierarchical parent-child context resolution, payload filtering, and granular stage latency telemetry.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
import numpy as np
from qdrant_client import QdrantClient, models
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Global singletons for model and Qdrant client to eliminate initialization overhead on query path
_EMBEDDING_MODEL: Optional[SentenceTransformer] = None
_QDRANT_CLIENT: Optional[QdrantClient] = None
_PARENT_CACHE: Dict[str, str] = {}


def get_embedding_model(model_name: str = "BAAI/bge-m3") -> SentenceTransformer:
    """Get or initialize singleton SentenceTransformer embedding model."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer(model_name)
    return _EMBEDDING_MODEL


def get_qdrant_client() -> QdrantClient:
    """Get or initialize singleton authenticated Qdrant client."""
    global _QDRANT_CLIENT
    if _QDRANT_CLIENT is None:
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if not url:
            raise ValueError("QDRANT_URL is not configured in backend/.env")
        _QDRANT_CLIENT = QdrantClient(url=url, api_key=api_key, timeout=10.0)
    return _QDRANT_CLIENT


_PUNCTUATION_CHARS = set(".,!?:;\"'()[]{}<>/\\|`~@#$%^&*+-=_।॥\n\r\t«»—–")


def _tokenize_indic_text(text: str) -> List[str]:
    """Tokenize multilingual/Indic text into words/tokens for BM25 sparse scoring.

    Preserves full Indic script characters, matras (vowel signs), and conjuncts.
    """
    words = text.strip().split()
    tokens: List[str] = []
    for w in words:
        clean = "".join(ch for ch in w if ch not in _PUNCTUATION_CHARS).strip()
        if clean:
            tokens.append(clean.lower())
    return tokens if tokens else [text.lower()]



def compute_reciprocal_rank_fusion(
    dense_hits: Sequence[Any],
    sparse_scores: Sequence[Tuple[Any, float]],
    rrf_k: int = 60,
) -> List[Tuple[Any, float]]:
    """Fuse dense and sparse retrieval ranks using Reciprocal Rank Fusion (RRF).

    Score(d) = sum( 1 / (rrf_k + rank_i(d)) ) for each ranking source.
    """
    rrf_map: Dict[str, Tuple[Any, float]] = {}

    # Dense ranks
    for rank, hit in enumerate(dense_hits):
        hit_id = str(hit.id)
        score = 1.0 / (rrf_k + (rank + 1))
        rrf_map[hit_id] = (hit, score)

    # Sparse ranks (sorted by descending BM25 score)
    sorted_sparse = sorted(sparse_scores, key=lambda x: x[1], reverse=True)
    for rank, (hit, bm25_score) in enumerate(sorted_sparse):
        hit_id = str(hit.id)
        sparse_rrf = 1.0 / (rrf_k + (rank + 1))
        if hit_id in rrf_map:
            existing_hit, existing_score = rrf_map[hit_id]
            rrf_map[hit_id] = (existing_hit, existing_score + sparse_rrf)
        else:
            rrf_map[hit_id] = (hit, sparse_rrf)

    # Sort merged results by combined RRF score descending
    merged = sorted(rrf_map.values(), key=lambda x: x[1], reverse=True)
    return merged


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=0.5, min=0.5, max=2))
def _execute_qdrant_search(
    client: QdrantClient,
    collection_name: str,
    query_vector: List[float],
    top_k: int,
    query_filter: Optional[models.Filter],
) -> List[Any]:
    """Execute dense vector query against Qdrant with exponential backoff retry."""
    if hasattr(client, "query_points"):
        res = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return list(res.points) if hasattr(res, "points") else list(res)
    else:
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )



async def retrieve(
    query: str,
    top_k: int = 5,
    language: Optional[str] = None,
    strategy: Optional[str] = None,
    collection_name: str = "msmarco_indic_rag",
    model_name: str = "BAAI/bge-m3",
    rrf_k: int = 60,
    dense_fetch_k: int = 20,
) -> Dict[str, Any]:
    """Execute low-latency hybrid retrieval across Qdrant with per-stage timing telemetry.

    Args:
        query: User input search/question text.
        top_k: Number of final merged results to return (default: 5).
        language: Optional language filter (e.g. 'hin', 'tam').
        strategy: Optional chunking strategy filter ('passage_native', 'fixed_size', 'semantic', 'hierarchical_child', 'hierarchical_parent').
        collection_name: Qdrant collection name.
        model_name: Embedding model identifier.
        rrf_k: Reciprocal Rank Fusion constant (default: 60).
        dense_fetch_k: Number of candidates fetched from vector search prior to fusion.

    Returns:
        Dict with keys 'results', 'timings_ms', 'query', 'language', 'strategy'.
    """
    total_start = time.perf_counter()
    timings: Dict[str, float] = {}

    clean_query = query.strip()
    if not clean_query:
        return {
            "results": [],
            "timings_ms": {"total_retrieval_ms": 0.0},
            "query": query,
            "language": language,
            "strategy": strategy,
        }

    # 1. Embed query
    t_embed_0 = time.perf_counter()
    model = get_embedding_model(model_name)
    # Run embedding in default executor to keep event loop responsive
    loop = asyncio.get_running_loop()
    query_vec = await loop.run_in_executor(
        None,
        lambda: model.encode(clean_query, normalize_embeddings=True).tolist(),
    )
    timings["embed_ms"] = round((time.perf_counter() - t_embed_0) * 1000, 2)

    # 2. Build payload filter
    must_conditions = []
    if language:
        must_conditions.append(
            models.FieldCondition(key="language", match=models.MatchValue(value=language.lower()))
        )
    if strategy:
        must_conditions.append(
            models.FieldCondition(key="strategy", match=models.MatchValue(value=strategy))
        )
    qdrant_filter = models.Filter(must=must_conditions) if must_conditions else None

    # 3. Dense vector search against Qdrant
    t_dense_0 = time.perf_counter()
    client = get_qdrant_client()
    fetch_limit = max(dense_fetch_k, top_k * 2)
    dense_hits = await loop.run_in_executor(
        None,
        lambda: _execute_qdrant_search(client, collection_name, query_vec, fetch_limit, qdrant_filter),
    )
    timings["dense_search_ms"] = round((time.perf_counter() - t_dense_0) * 1000, 2)

    if not dense_hits:
        total_time = round((time.perf_counter() - total_start) * 1000, 2)
        timings["sparse_search_ms"] = 0.0
        timings["fusion_ms"] = 0.0
        timings["parent_resolution_ms"] = 0.0
        timings["total_retrieval_ms"] = total_time
        return {
            "results": [],
            "timings_ms": timings,
            "query": clean_query,
            "language": language,
            "strategy": strategy,
        }

    # 4. Sparse BM25 search over candidate chunk set
    t_sparse_0 = time.perf_counter()
    query_tokens = _tokenize_indic_text(clean_query)
    candidate_corpus = [_tokenize_indic_text(h.payload.get("text", "")) for h in dense_hits]
    bm25 = BM25Okapi(candidate_corpus)
    doc_scores = bm25.get_scores(query_tokens)
    sparse_scores = [(dense_hits[i], float(doc_scores[i])) for i in range(len(dense_hits))]
    timings["sparse_search_ms"] = round((time.perf_counter() - t_sparse_0) * 1000, 2)

    # 5. Reciprocal Rank Fusion (RRF)
    t_fusion_0 = time.perf_counter()
    fused_results = compute_reciprocal_rank_fusion(dense_hits, sparse_scores, rrf_k=rrf_k)
    top_fused = fused_results[:top_k]
    timings["fusion_ms"] = round((time.perf_counter() - t_fusion_0) * 1000, 2)

    # 6. Hierarchical Parent Context Resolution
    t_parent_0 = time.perf_counter()
    formatted_results: List[Dict[str, Any]] = []

    for hit, score in top_fused:
        payload = dict(hit.payload or {})
        chunk_strategy = payload.get("strategy", "")
        parent_id = payload.get("parent_id")
        resolved_context = payload.get("text", "")

        # If child chunk, resolve parent passage for comprehensive generation context
        if parent_id and (chunk_strategy == "hierarchical_child" or "child" in chunk_strategy):
            if parent_id in _PARENT_CACHE:
                resolved_context = _PARENT_CACHE[parent_id]
            else:
                try:
                    # Query parent chunk from Qdrant by parent_id
                    parent_points = await loop.run_in_executor(
                        None,
                        lambda pid=parent_id: client.scroll(
                            collection_name=collection_name,
                            scroll_filter=models.Filter(
                                must=[models.FieldCondition(key="chunk_id", match=models.MatchValue(value=pid))]
                            ),
                            limit=1,
                            with_payload=True,
                        )[0],
                    )
                    if parent_points:
                        parent_text = parent_points[0].payload.get("text", "")
                        if parent_text:
                            _PARENT_CACHE[parent_id] = parent_text
                            resolved_context = parent_text
                except Exception:
                    pass  # Fall back to child text on resolution error

        formatted_results.append({
            "chunk_id": payload.get("chunk_id", str(hit.id)),
            "score": round(float(score), 4),
            "dense_score": round(float(hit.score), 4) if hasattr(hit, "score") and hit.score is not None else None,
            "text": payload.get("text", ""),
            "resolved_context": resolved_context,
            "strategy": chunk_strategy,
            "language": payload.get("language"),
            "source_doc_id": payload.get("source_doc_id"),
            "query_id": payload.get("query_id"),
            "is_selected": payload.get("is_selected", False),
            "ground_truth_answer": payload.get("answer_ground_truth", ""),
            "metadata": payload,
        })

    timings["parent_resolution_ms"] = round((time.perf_counter() - t_parent_0) * 1000, 2)
    timings["total_retrieval_ms"] = round((time.perf_counter() - total_start) * 1000, 2)

    return {
        "results": formatted_results,
        "timings_ms": timings,
        "query": clean_query,
        "language": language,
        "strategy": strategy,
    }
