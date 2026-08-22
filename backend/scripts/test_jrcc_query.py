"""Test JRCC Query Script with Fine-Grained Score & Latency Logging (HH Goa 2026).

Executes the exact Rachel Carson (JRCC) query across chunking strategies
with DEBUG=1 logging to verify raw dense score, BM25 score, RRF score,
exact confidence threshold comparisons, and raw Qdrant search wall-clock latency.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

# Ensure UTF-8 output encoding on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Set DEBUG flag
os.environ["DEBUG"] = "1"

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.retrieval import retrieve
from src.harness import run_rag_pipeline

QUERY_HIN = "रेचल कार्सन ने पर्यावरण के बारे में क्या लिखा?"
QUERY_DESC = "Rachel Carson environmental obligation / Silent Spring query in Hindi"


async def main():
    print("=" * 80)
    print("DEBUG TEST: JRCC-STYLE QUERY RETRIEVAL & GUARDRAILS AUDIT")
    print(f"Query: \"{QUERY_HIN}\"")
    print(f"Description: {QUERY_DESC}")
    print("=" * 80)

    # 1. Direct Retrieval across strategies
    strategies = ["passage_native", "fixed_size", "semantic", "hierarchical_child"]
    for strat in strategies:
        print(f"\n==================== EVALUATING STRATEGY: {strat.upper()} ====================")
        res = await retrieve(query=QUERY_HIN, top_k=3, language="hin", strategy=strat)
        t = res["timings_ms"]
        print(f"[TIMING SUMMARY] Total={t.get('total_retrieval_ms')}ms | Embed={t.get('embed_ms')}ms | Raw Qdrant Vector Call={t.get('raw_qdrant_ms')}ms | Dense Total={t.get('dense_search_ms')}ms | BM25={t.get('sparse_search_ms')}ms | Fusion={t.get('fusion_ms')}ms | Parent Res={t.get('parent_resolution_ms')}ms")

    # 2. Full End-to-End Pipeline Harness Run
    print("\n==================== FULL END-TO-END RAG PIPELINE RUN ====================")
    pipeline_res = await run_rag_pipeline(
        query=QUERY_HIN,
        language_hint="hin",
        strategy="passage_native",
    )

    print("\n[PIPELINE OUTPUT]")
    print(f"Transcript / Query : {pipeline_res.get('query')}")
    print(f"Answer             : {pipeline_res.get('answer')}")
    print(f"Guardrail Flags    : {pipeline_res.get('guardrail_flags')}")
    print(f"Timings (ms)       : {pipeline_res.get('timings_ms')}")
    print(f"Sources Count      : {len(pipeline_res.get('sources', []))}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
