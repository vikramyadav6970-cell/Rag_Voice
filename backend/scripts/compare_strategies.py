"""Compare Chunking Strategies Script — Offline Evaluation & Side-by-Side Analysis.

Executes test queries across all 4 chunking strategies in Qdrant Cloud,
comparing relevance, context quality, resolved parent text, and sub-stage latencies.
"""

import asyncio
import os
import sys
import time
from typing import Any, Dict, List

from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.retrieval import retrieve

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

TEST_QUERIES = [
    {
        "query": "कॉर्पोरेशन क्या है?",
        "lang": "hin",
        "description": "Definition / Entity query in Hindi (What is a corporation?)",
    },
    {
        "query": "रेचल कार्सन ने पर्यावरण के बारे में क्या लिखा?",
        "lang": "hin",
        "description": "Causal / Explanatory query in Hindi (Rachel Carson environmental obligation)",
    },
    {
        "query": "பொட்டாசியம் குறைந்த உணவுகளின் பட்டியல் என்ன?",
        "lang": "tam",
        "description": "List query in Tamil (Foods low in potassium)",
    },
]

STRATEGIES = [
    "passage_native",
    "fixed_size",
    "semantic",
    "hierarchical_child",
]


async def run_comparison() -> None:
    """Run evaluation comparing all chunking strategies side-by-side."""
    print("=" * 80)
    print("CHUNKING STRATEGY RETRIEVAL COMPARISON (HH GOA 2026)")
    print("Evaluating: Passage Native vs. Fixed-Size vs. Semantic vs. Hierarchical")
    print("=" * 80 + "\n")

    for q_idx, item in enumerate(TEST_QUERIES):
        query_text = item["query"]
        lang = item["lang"]
        desc = item["description"]

        print("\n" + "#" * 80)
        print(f"QUERY #{q_idx + 1}: {query_text} [{lang.upper()}]")
        print(f"Description: {desc}")
        print("#" * 80)

        for strat in STRATEGIES:
            print(f"\n--- Strategy: {strat.upper()} ---")
            res = await retrieve(query=query_text, top_k=2, language=lang, strategy=strat)
            hits = res.get("results", [])
            timings = res.get("timings_ms", {})

            print(f"Latency: Total={timings.get('total_retrieval_ms')}ms | Embed={timings.get('embed_ms')}ms | Dense={timings.get('dense_search_ms')}ms | Sparse={timings.get('sparse_search_ms')}ms | Fusion={timings.get('fusion_ms')}ms")

            if not hits:
                print("  [No hits found for this strategy and language filter]")
                continue

            for h_idx, hit in enumerate(hits):
                score = hit.get("score")
                text = hit.get("text", "")
                resolved = hit.get("resolved_context", "")
                is_sel = hit.get("is_selected", False)
                doc_id = hit.get("source_doc_id")

                print(f"  Result #{h_idx + 1} (Score: {score}, Ground Truth Match: {is_sel}, Doc: {doc_id}):")
                print(f"    - Matched Chunk : {text[:140]}...")
                if strat == "hierarchical_child" and resolved != text:
                    print(f"    - Resolved Parent Context ({len(resolved)} chars): {resolved[:160]}...")

    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_comparison())
