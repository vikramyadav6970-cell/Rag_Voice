"""Generation Service — Grounded LLM Synthesis via Fast Inference API (xAI / OpenAI / Fallback).

Enforces strict context grounding, refusal on missing evidence,
streaming time-to-first-token tracking, tenacity retry policies, and latency telemetry.
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import httpx
from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Constants & Default Configurations
DEFAULT_MODEL = os.getenv("GENERATION_MODEL", "grok-2-mini")
DEFAULT_BASE_URL = os.getenv("GENERATION_BASE_URL", "https://api.x.ai/v1")

# Standardized Grounding Refusal Sentinels
REFUSAL_PHRASE_EN = "I do not have sufficient information in the provided context to answer this question."
REFUSAL_PHRASE_HI = "दी गई जानकारी के आधार पर इस प्रश्न का उत्तर उपलब्ध नहीं है।"

SYSTEM_GROUNDING_PROMPT = """You are a grounded factual AI assistant for a multilingual Retrieval-Augmented Generation (RAG) system.

CRITICAL INSTRUCTIONS:
1. Answer the user's question STRICTLY and ONLY using the provided Context Passages.
2. DO NOT assume, extrapolate, or bring in outside knowledge not present in the context.
3. If the context does not contain enough information to fully and factually answer the question, you MUST explicitly respond with:
   "I do not have sufficient information in the provided context to answer this question." (or its equivalent in the language of the query).
4. Respond in the SAME language as the query (e.g., Hindi for Hindi queries, Tamil for Tamil, English for English).
5. Keep your answer direct, clear, concise, and completely grounded in the retrieved facts.
"""


def _get_async_openai_client() -> AsyncOpenAI:
    """Initialize AsyncOpenAI client configured for xAI / fast inference provider."""
    api_key = os.getenv("GENERATION_API_KEY", "")
    base_url = os.getenv("GENERATION_BASE_URL", DEFAULT_BASE_URL)
    return AsyncOpenAI(
        api_key=api_key.strip() if api_key else "dummy-key",
        base_url=base_url.strip(),
        timeout=10.0,
    )


def format_context_for_prompt(context_chunks: List[Dict[str, Any]]) -> str:
    """Format list of retrieved context chunks into structured prompt text."""
    if not context_chunks:
        return "[No relevant context passages provided.]"

    formatted_parts: List[str] = []
    for idx, chunk in enumerate(context_chunks, 1):
        content = chunk.get("resolved_context") or chunk.get("text") or ""
        doc_id = chunk.get("source_doc_id", f"doc_{idx}")
        strategy = chunk.get("strategy", "unknown")
        score = chunk.get("score", "")

        formatted_parts.append(
            f"--- [Passage {idx}] (ID: {doc_id}, Strategy: {strategy}, Relevance: {score}) ---\n{content.strip()}"
        )

    return "\n\n".join(formatted_parts)


def _is_english_query(text: str) -> bool:
    """Check if query is primarily in English / Latin script."""
    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    total_alpha = sum(1 for c in text if c.isalpha())
    return (latin_chars / max(total_alpha, 1)) > 0.6


def _translate_indic_to_english(indic_text: str) -> str:
    """Translate Indic (Hindi/Tamil) grounded passage into fluent English via Sarvam AI."""
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        return indic_text
    try:
        # Determine source script: Devanagari (0900-097F) or Tamil (0B80-0BFF)
        has_tamil = any(0x0B80 <= ord(c) <= 0x0BFF for c in indic_text)
        src_lang = "ta-IN" if has_tamil else "hi-IN"
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(
                "https://api.sarvam.ai/translate",
                headers={"api-subscription-key": api_key.strip()},
                json={
                    "input": indic_text[:450],
                    "source_language_code": src_lang,
                    "target_language_code": "en-IN",
                    "mode": "formal",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                translated = data.get("translated_text", "").strip()
                if translated:
                    return translated
    except Exception as exc:
        print(f"[Generation] Translation warning: {exc}")
    return indic_text


def _extractive_grounded_fallback(query: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Deterministic grounded extractive fallback for offline/no-credit runtime scenarios.

    Extracts the highest-grounded passage sentence containing key terms from the query.
    """
    if not context_chunks:
        return REFUSAL_PHRASE_EN

    # Extract clean keywords from query
    query_words = [w.strip("?,.!।") for w in query.split() if len(w.strip("?,.!।")) > 1]
    
    best_passage = ""
    best_score = -1

    for chunk in context_chunks:
        text = chunk.get("resolved_context") or chunk.get("text") or ""
        if not text:
            continue

        # Check keyword matches
        matches = sum(1 for w in query_words if w.lower() in text.lower())
        if matches > best_score:
            best_score = matches
            best_passage = text

    if not best_passage:
        best_passage = context_chunks[0].get("resolved_context") or context_chunks[0].get("text", "")

    # Clean and return concise grounded passage summary
    sentences = re.split(r"[।\n.!?]+", best_passage)
    concise = " ".join(s.strip() for s in sentences if s.strip())
    concise_summary = concise[:320].strip() + ("..." if len(concise) > 320 else "")

    # If user queried in English, translate the Indic passage to English
    if _is_english_query(query):
        return _translate_indic_to_english(concise_summary)

    return concise_summary



@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
    reraise=True,
)
async def _execute_llm_completion(
    client: AsyncOpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: int = 400,
) -> Tuple[str, Optional[float]]:
    """Execute streaming LLM completion to capture Time-To-First-Token (TTFT) and full text."""
    t_call_start = time.perf_counter()
    ttft_ms: Optional[float] = None
    accumulated_tokens: List[str] = []

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    async for chunk in stream:
        if ttft_ms is None:
            ttft_ms = round((time.perf_counter() - t_call_start) * 1000, 2)
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            accumulated_tokens.append(chunk.choices[0].delta.content)

    full_answer = "".join(accumulated_tokens).strip()
    return full_answer, ttft_ms


async def generate(
    query: str,
    context_chunks: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 400,
    timeout_sec: float = 10.0,
) -> Dict[str, Any]:
    """Generate a strictly grounded answer from retrieved context passages.

    Args:
        query: User input query / question.
        context_chunks: List of retrieved context dictionaries.
        model: Optional model override (defaults to GENERATION_MODEL / 'grok-2-mini').
        temperature: Sampling temperature (low default 0.1 for high factual grounding).
        max_tokens: Maximum tokens to generate.
        timeout_sec: Maximum timeout in seconds.

    Returns:
        Dict containing:
        {
            "answer": str,
            "latency_ms": float,
            "ttft_ms": float | None,
            "model": str,
            "success": bool,
            "error": str | None,
            "is_grounded": bool,
        }
    """
    t_start = time.perf_counter()
    active_model = model or os.getenv("GENERATION_MODEL") or DEFAULT_MODEL

    clean_query = query.strip()
    if not clean_query:
        return {
            "answer": "No question provided.",
            "latency_ms": 0.0,
            "ttft_ms": None,
            "model": active_model,
            "success": False,
            "error": "Empty query provided.",
            "is_grounded": False,
        }

    # Short-circuit if no context chunks are supplied
    if not context_chunks:
        latency = round((time.perf_counter() - t_start) * 1000, 2)
        return {
            "answer": REFUSAL_PHRASE_EN,
            "latency_ms": latency,
            "ttft_ms": latency,
            "model": active_model,
            "success": True,
            "error": None,
            "is_grounded": True,
        }

    formatted_context = format_context_for_prompt(context_chunks)
    user_prompt = f"Context Passages:\n{formatted_context}\n\nQuestion:\n{clean_query}\n\nAnswer:"

    messages = [
        {"role": "system", "content": SYSTEM_GROUNDING_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        client = _get_async_openai_client()
        answer, ttft_ms = await _execute_llm_completion(
            client=client,
            model=active_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        # Check if model expressed lack of grounding/knowledge
        lower_ans = answer.lower()
        is_refusal = (
            "not have sufficient information" in lower_ans
            or "not enough information" in lower_ans
            or "उत्तर उपलब्ध नहीं है" in answer
            or "जानकारी उपलब्ध नहीं है" in answer
            or "தகவல் இல்லை" in answer
        )

        return {
            "answer": answer,
            "latency_ms": total_latency_ms,
            "ttft_ms": ttft_ms,
            "model": active_model,
            "success": True,
            "error": None,
            "is_grounded": not is_refusal,
            "context_count": len(context_chunks),
        }

    except Exception as exc:
        total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        err_msg = str(exc)

        # Graceful grounded extractive fallback when remote API lacks credits/network
        fallback_answer = _extractive_grounded_fallback(clean_query, context_chunks)
        return {
            "answer": fallback_answer,
            "latency_ms": total_latency_ms,
            "ttft_ms": total_latency_ms,
            "model": f"{active_model} (grounded-fallback)",
            "success": True,
            "error": f"Upstream API warning: {err_msg[:120]}",
            "is_grounded": True,
            "context_count": len(context_chunks),
        }
