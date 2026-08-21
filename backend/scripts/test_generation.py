"""Test script for Generation Service with live context."""

import asyncio
import os
import sys

from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.generation import generate
from src.retrieval import retrieve

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def run_generation_test() -> None:
    """Test grounded generation with live Qdrant retrieval context."""
    print("=" * 70)
    print("TESTING GROUNDED LLM GENERATION SERVICE (xAI Grok-2-mini)")
    print("=" * 70 + "\n")

    query = "कॉर्पोरेशन क्या है?"
    print(f"Query: {query} [Hindi]\n")

    print("1. Retrieving context chunks from Qdrant Cloud...")
    retrieval_res = await retrieve(query=query, top_k=3, language="hin")
    chunks = retrieval_res.get("results", [])
    print(f"   Retrieved {len(chunks)} chunks in {retrieval_res['timings_ms']['total_retrieval_ms']}ms\n")

    print("2. Generating grounded answer via xAI Grok-2-mini...")
    gen_res = await generate(query=query, context_chunks=chunks)

    print("\n" + "-" * 70)
    print("GENERATION RESPONSE")
    print("-" * 70)
    print(f"Success          : {gen_res.get('success')}")
    print(f"Model            : {gen_res.get('model')}")
    print(f"TTFT Latency     : {gen_res.get('ttft_ms')} ms")
    print(f"Total Latency    : {gen_res.get('latency_ms')} ms")
    print(f"Is Grounded      : {gen_res.get('is_grounded')}")
    print(f"\nGenerated Answer :\n{gen_res.get('answer')}")

    print("\n" + "=" * 70)
    print("3. Testing Grounding Refusal on Empty Context...")
    refusal_res = await generate(query="What is a quantum computer?", context_chunks=[])
    print(f"Empty Context Response: '{refusal_res.get('answer')}' (Grounded Refusal: {refusal_res.get('is_grounded')})")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_generation_test())
