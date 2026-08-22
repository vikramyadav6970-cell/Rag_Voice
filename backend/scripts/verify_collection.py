"""Qdrant Collection Verification & Health Audit Script (HH Goa 2026).

Scrolls the active Qdrant Cloud collection, computes exact point counts,
tallies breakdowns across languages and chunking strategies, and displays
representative payload samples for verification and process logging.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

# Ensure standard UTF-8 console output across Windows & Linux
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment configuration
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def get_qdrant_client() -> QdrantClient:
    """Initialize authenticated Qdrant client from environment variables."""
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url:
        raise ValueError("QDRANT_URL is not set in backend/.env")
    return QdrantClient(url=url, api_key=api_key, timeout=60.0, check_compatibility=False)


def verify_collection(
    collection_name: str = "msmarco_indic_rag",
    sample_size: int = 3,
    scroll_batch_size: int = 500,
) -> Dict[str, Any]:
    """Scroll through Qdrant collection and audit point count, language/strategy distributions, and payloads."""
    client = get_qdrant_client()

    print("=" * 70, flush=True)
    print("QDRANT COLLECTION AUDIT & VERIFICATION", flush=True)
    print(f"Collection Name : {collection_name}", flush=True)
    print(f"Target Instance : {os.getenv('QDRANT_URL', '').split('@')[-1]}", flush=True)
    print("=" * 70, flush=True)

    t0 = time.perf_counter()

    # 1. Fetch Collection Metadata
    try:
        col_info = client.get_collection(collection_name=collection_name)
    except Exception as exc:
        print(f"\n[Error] Could not retrieve collection '{collection_name}': {exc}", flush=True)
        sys.exit(1)

    points_reported = col_info.points_count
    vectors_count = getattr(col_info, "vectors_count", points_reported)
    status = getattr(col_info, "status", "unknown")

    print(f"\n[Collection Status: {status}]", flush=True)
    print(f"Reported Points Count: {points_reported:,}", flush=True)
    print(f"Reported Vectors Count: {vectors_count:,}", flush=True)

    # 2. Scroll and Aggregate Payloads
    print(f"\nScrolling points in batches of {scroll_batch_size}...", flush=True)
    next_offset: Optional[Any] = None
    total_scrolled = 0
    lang_counts: Dict[str, int] = {}
    strategy_counts: Dict[str, int] = {}
    samples: List[Dict[str, Any]] = []

    while True:
        records, next_offset = client.scroll(
            collection_name=collection_name,
            limit=scroll_batch_size,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
        )

        if not records:
            break

        for record in records:
            total_scrolled += 1
            payload = record.payload or {}
            
            lang = str(payload.get("language", "unknown"))
            strat = str(payload.get("strategy", "unknown"))

            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1

            if len(samples) < sample_size:
                samples.append({
                    "id": str(record.id),
                    "chunk_id": payload.get("chunk_id"),
                    "source_doc_id": payload.get("source_doc_id"),
                    "language": lang,
                    "strategy": strat,
                    "text_preview": (payload.get("text", "") or "")[:120] + ("..." if len(payload.get("text", "") or "") > 120 else ""),
                    "query_text": payload.get("query_text") or payload.get("query_hin") or payload.get("query_eng") or "N/A",
                })

        print(f"  Scrolled {total_scrolled:,}/{points_reported:,} points...", flush=True)

        if next_offset is None:
            break

    elapsed = time.perf_counter() - t0

    # 3. Print Formatted Report
    print("\n" + "=" * 70, flush=True)
    print("VERIFICATION SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"Total Scrolled Points : {total_scrolled:,} (Audit matches reported: {total_scrolled == points_reported})", flush=True)
    print(f"Scroll Time Elapsed   : {elapsed:.2f}s", flush=True)
    
    print("\n--- Language Distribution ---", flush=True)
    for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_scrolled * 100) if total_scrolled > 0 else 0
        print(f"  - {lang:<12}: {count:>6,} points ({pct:5.1f}%)", flush=True)

    print("\n--- Strategy Distribution ---", flush=True)
    for strat, count in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_scrolled * 100) if total_scrolled > 0 else 0
        print(f"  - {strat:<22}: {count:>6,} points ({pct:5.1f}%)", flush=True)

    print("\n--- Sample Payloads ---", flush=True)
    for idx, sample in enumerate(samples, 1):
        print(f"Sample #{idx}:", flush=True)
        print(f"  Point ID     : {sample['id']}", flush=True)
        print(f"  Chunk ID     : {sample['chunk_id']}", flush=True)
        print(f"  Doc ID       : {sample['source_doc_id']}", flush=True)
        print(f"  Language     : {sample['language']}", flush=True)
        print(f"  Strategy     : {sample['strategy']}", flush=True)
        print(f"  Query Context: {sample['query_text']}", flush=True)
        print(f"  Text Preview : {sample['text_preview']}", flush=True)
        print(flush=True)

    print("=" * 70, flush=True)

    return {
        "total_points": total_scrolled,
        "language_breakdown": lang_counts,
        "strategy_breakdown": strategy_counts,
        "samples": samples,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify and audit Qdrant collection contents")
    parser.add_argument("--collection", "-c", default="msmarco_indic_rag", help="Collection name")
    parser.add_argument("--samples", "-s", type=int, default=3, help="Number of payload samples to print")
    parser.add_argument("--batch-size", "-b", type=int, default=500, help="Scroll batch size")
    args = parser.parse_args()

    verify_collection(
        collection_name=args.collection,
        sample_size=args.samples,
        scroll_batch_size=args.batch_size,
    )
