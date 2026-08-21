"""Pipeline Orchestration Harness — End-to-End Multilingual Voice RAG State Machine.

Orchestration Architecture Choice:
We implement an Explicit Python Async State Machine (`RAGPipelineHarness`).
Rationale:
1. Zero Dependency Overhead: Eliminates bloated runtime graph dependencies and execution overhead, preserving sub-200ms latency budgets.
2. Step Isolation: Each pipeline step is an independent async method operating on an immutable/explicit state container (`PipelineContext`), allowing individual steps to be retried or evaluated in isolation.
3. Clean Phase 4 Guardrail Hooks: Explicit hook slots for input safety, retrieval confidence filtering, and output grounding verification.
4. Granular Telemetry: Every pipeline sub-step records fine-grained millisecond latencies directly into a shared telemetry dict.

Execution Flow:
1. `transcribe_audio`: Converts voice input to text via Sarvam AI Saaras v3.
2. `validate_input` [Phase 4 Hook]: Checks input safety and topicality.
3. `retrieve_context`: Executes hybrid dense+sparse retrieval against Qdrant Cloud.
4. `check_retrieval_confidence` [Phase 4 Hook]: Verifies retrieval score confidence threshold.
5. `generate_answer`: Synthesizes grounded answer from retrieved context passages.
6. `check_grounding` [Phase 4 Hook]: Verifies answer factual grounding and hallucination status.
7. `return_result`: Bundles final answer, sources, timings, and guardrail flags.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.generation import generate
from src.guardrails import (
    check_grounding_hook,
    check_retrieval_confidence_hook,
    validate_input_query,
)
from src.retrieval import retrieve

from src.stt import transcribe

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))



@dataclass
class PipelineContext:
    """Explicit state container flowing through pipeline execution steps."""
    # Inputs
    audio_bytes: Optional[bytes] = None
    audio_filename: str = "audio.wav"
    query: str = ""
    language_hint: Optional[str] = None
    strategy: Optional[str] = None
    top_k: int = 4

    # Intermediate / Output State
    transcript: str = ""
    detected_language: Optional[str] = None
    context_chunks: List[Dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    
    # Telemetry & Diagnostics
    timings_ms: Dict[str, float] = field(default_factory=dict)
    guardrail_flags: Dict[str, Any] = field(default_factory=lambda: {
        "input_safe": True,
        "input_offtopic": False,
        "retrieval_confident": True,
        "output_grounded": True,
    })
    errors: Dict[str, str] = field(default_factory=dict)
    success: bool = True
    stop_early: bool = False


class RAGPipelineHarness:
    """Async state machine orchestrating Voice RAG with independent step execution and fallbacks."""

    def __init__(self) -> None:
        # Phase 4 Guardrail hooks (pluggable callbacks)
        self.input_guardrail_hook: Optional[Callable[[str], Coroutine[Any, Any, Dict[str, Any]]]] = None
        self.retrieval_confidence_hook: Optional[Callable[[List[Dict[str, Any]]], Coroutine[Any, Any, bool]]] = None
        self.grounding_guardrail_hook: Optional[Callable[[str, List[Dict[str, Any]]], Coroutine[Any, Any, bool]]] = None

    # --- Step 1: Speech-to-Text ---
    async def step_transcribe_audio(self, ctx: PipelineContext) -> PipelineContext:
        """Step 1: Transcribe audio input if audio bytes are present."""
        if not ctx.audio_bytes or len(ctx.audio_bytes) == 0:
            # If direct query text was provided, skip audio transcription step
            ctx.timings_ms["stt_ms"] = 0.0
            return ctx

        t_0 = time.perf_counter()
        try:
            stt_res = await transcribe(
                audio_bytes=ctx.audio_bytes,
                language_hint=ctx.language_hint,
                filename=ctx.audio_filename,
            )

            ctx.timings_ms["stt_ms"] = stt_res.get("latency_ms", round((time.perf_counter() - t_0) * 1000, 2))

            if stt_res.get("success") and stt_res.get("text"):
                ctx.transcript = stt_res["text"].strip()
                ctx.query = ctx.transcript
                ctx.detected_language = stt_res.get("detected_language") or ctx.language_hint
            else:
                # Specific graceful fallback on transcription failure
                ctx.transcript = ""
                ctx.query = ""
                ctx.errors["stt"] = stt_res.get("error") or "Speech recognition returned empty transcript."
                ctx.answer = "Could not understand the audio clearly. Please try speaking again."
                ctx.success = False
                ctx.stop_early = True
        except Exception as exc:
            ctx.timings_ms["stt_ms"] = round((time.perf_counter() - t_0) * 1000, 2)
            ctx.errors["stt"] = str(exc)
            ctx.answer = "Audio transcription encountered an issue. Please try again."
            ctx.success = False
            ctx.stop_early = True

        return ctx

    # --- Step 2: Input Validation & Guardrails [Phase 4 Hook] ---
    async def step_validate_input(self, ctx: PipelineContext) -> PipelineContext:
        """Step 2: Validate input query safety and domain topicality."""
        if ctx.stop_early or not ctx.query:
            return ctx

        t_0 = time.perf_counter()
        try:
            if self.input_guardrail_hook:
                guard_res = await self.input_guardrail_hook(ctx.query)
                ctx.guardrail_flags.update(guard_res)
                if not guard_res.get("input_safe", True):
                    ctx.answer = "I cannot process this request as it contains unsafe or prohibited content."
                    ctx.stop_early = True
                elif guard_res.get("input_offtopic", False):
                    ctx.answer = "This question is outside the scope of the knowledge base."
                    ctx.stop_early = True
        except Exception as exc:
            ctx.errors["input_guardrail"] = str(exc)
        finally:
            ctx.timings_ms["input_guardrail_ms"] = round((time.perf_counter() - t_0) * 1000, 2)

        return ctx

    # --- Step 3: Context Retrieval ---
    async def step_retrieve_context(self, ctx: PipelineContext) -> PipelineContext:
        """Step 3: Run multilingual hybrid search against Qdrant Cloud."""
        if ctx.stop_early or not ctx.query:
            return ctx

        t_0 = time.perf_counter()
        # Derive language for retrieval (prefer detected language code e.g. 'hin'/'tam')
        retrieval_lang = None
        if ctx.detected_language:
            retrieval_lang = ctx.detected_language.split("-")[0]
        elif ctx.language_hint:
            retrieval_lang = ctx.language_hint.split("-")[0]

        try:
            retrieval_res = await retrieve(
                query=ctx.query,
                top_k=ctx.top_k,
                language=retrieval_lang,
                strategy=ctx.strategy,
            )
            ctx.context_chunks = retrieval_res.get("results", [])
            retrieval_timings = retrieval_res.get("timings_ms", {})
            
            ctx.timings_ms["retrieval_ms"] = retrieval_timings.get("total_retrieval_ms", round((time.perf_counter() - t_0) * 1000, 2))
            ctx.timings_ms["embed_ms"] = retrieval_timings.get("embed_ms", 0.0)
            ctx.timings_ms["dense_search_ms"] = retrieval_timings.get("dense_search_ms", 0.0)
            ctx.timings_ms["sparse_search_ms"] = retrieval_timings.get("sparse_search_ms", 0.0)
            ctx.timings_ms["fusion_ms"] = retrieval_timings.get("fusion_ms", 0.0)

            if not ctx.context_chunks:
                ctx.guardrail_flags["retrieval_confident"] = False
        except Exception as exc:
            ctx.timings_ms["retrieval_ms"] = round((time.perf_counter() - t_0) * 1000, 2)
            ctx.errors["retrieval"] = str(exc)
            ctx.context_chunks = []
            ctx.guardrail_flags["retrieval_confident"] = False

        return ctx

    # --- Step 4: Retrieval Confidence Check [Phase 4 Hook] ---
    async def step_check_retrieval_confidence(self, ctx: PipelineContext) -> PipelineContext:
        """Step 4: Verify retrieval score quality before invoking LLM generation."""
        if ctx.stop_early or not ctx.query:
            return ctx


        t_0 = time.perf_counter()
        try:
            if self.retrieval_confidence_hook:
                is_confident = await self.retrieval_confidence_hook(ctx.context_chunks)
                ctx.guardrail_flags["retrieval_confident"] = is_confident
            else:
                ctx.guardrail_flags["retrieval_confident"] = len(ctx.context_chunks) > 0

            # Short-circuit generation if retrieval confidence is low
            if not ctx.guardrail_flags["retrieval_confident"]:
                ctx.answer = "I don't have enough grounded information to answer that."
                ctx.stop_early = True
        except Exception as exc:
            ctx.errors["retrieval_confidence"] = str(exc)
        finally:
            ctx.timings_ms["confidence_check_ms"] = round((time.perf_counter() - t_0) * 1000, 2)

        return ctx

    # --- Step 5: Grounded Answer Generation ---
    async def step_generate_answer(self, ctx: PipelineContext) -> PipelineContext:
        """Step 5: Generate grounded answer from context chunks."""
        if ctx.stop_early:
            return ctx

        t_0 = time.perf_counter()
        try:
            gen_res = await generate(
                query=ctx.query,
                context_chunks=ctx.context_chunks,
            )
            ctx.answer = gen_res.get("answer", "").strip()
            ctx.timings_ms["generation_ms"] = gen_res.get("latency_ms", round((time.perf_counter() - t_0) * 1000, 2))
            ctx.timings_ms["ttft_ms"] = gen_res.get("ttft_ms", 0.0)
            ctx.guardrail_flags["output_grounded"] = gen_res.get("is_grounded", True)
            
            if gen_res.get("error"):
                ctx.errors["generation_warning"] = gen_res["error"]
        except Exception as exc:
            ctx.timings_ms["generation_ms"] = round((time.perf_counter() - t_0) * 1000, 2)
            ctx.errors["generation"] = str(exc)
            ctx.answer = "I could not generate an answer due to an internal service error."
            ctx.success = False

        return ctx

    # --- Step 6: Grounding & Hallucination Check [Phase 4 Hook] ---
    async def step_check_grounding(self, ctx: PipelineContext) -> PipelineContext:
        """Step 6: Verify final generated answer against context evidence."""
        if ctx.stop_early or not ctx.answer:
            return ctx

        t_0 = time.perf_counter()
        try:
            if self.grounding_guardrail_hook:
                is_grounded = await self.grounding_guardrail_hook(ctx.answer, ctx.context_chunks)
                ctx.guardrail_flags["output_grounded"] = is_grounded
                
                # If grounding validation fails, replace ungrounded answer with refusal fallback
                if not is_grounded:
                    ctx.answer = "I don't have enough grounded information to answer that."
        except Exception as exc:
            ctx.errors["grounding_guardrail"] = str(exc)
        finally:
            ctx.timings_ms["grounding_check_ms"] = round((time.perf_counter() - t_0) * 1000, 2)

        return ctx

    # --- Main Execution Orchestrator ---
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        """Execute all pipeline steps sequentially with independent state tracking."""
        total_start = time.perf_counter()

        # Step 1: STT
        await self.step_transcribe_audio(ctx)

        # Step 2: Validate Input (Phase 4 hook)
        await self.step_validate_input(ctx)

        # Step 3: Retrieve Context
        await self.step_retrieve_context(ctx)

        # Step 4: Check Retrieval Confidence (Phase 4 hook)
        await self.step_check_retrieval_confidence(ctx)

        # Step 5: Generate Grounded Answer
        await self.step_generate_answer(ctx)

        # Step 6: Check Output Grounding (Phase 4 hook)
        await self.step_check_grounding(ctx)

        # Step 7: Finalize Timings
        ctx.timings_ms["total_pipeline_ms"] = round((time.perf_counter() - total_start) * 1000, 2)
        # Calculate retrieval-through-output latency (per Task 0.0 latency definition)
        retrieval_ms = ctx.timings_ms.get("retrieval_ms", 0.0)
        generation_ms = ctx.timings_ms.get("generation_ms", 0.0)
        ctx.timings_ms["retrieval_to_output_ms"] = round(retrieval_ms + generation_ms, 2)

        return ctx


# Default Singleton Pipeline Instance
pipeline = RAGPipelineHarness()
pipeline.input_guardrail_hook = validate_input_query
pipeline.retrieval_confidence_hook = check_retrieval_confidence_hook
pipeline.grounding_guardrail_hook = check_grounding_hook




async def run_rag_pipeline(
    audio_bytes: Optional[bytes] = None,
    audio_filename: str = "audio.wav",
    query: str = "",
    language_hint: Optional[str] = None,
    strategy: Optional[str] = None,
    top_k: int = 4,
) -> Dict[str, Any]:
    """Convenience helper to run the RAG pipeline harness and return standard dict payload."""
    ctx = PipelineContext(
        audio_bytes=audio_bytes,
        audio_filename=audio_filename,
        query=query,
        language_hint=language_hint,
        strategy=strategy,
        top_k=top_k,
    )
    result_ctx = await pipeline.execute(ctx)


    # Format simplified source citations
    sources = []
    for chunk in result_ctx.context_chunks:
        sources.append({
            "chunk_id": chunk.get("chunk_id"),
            "source_doc_id": chunk.get("source_doc_id"),
            "strategy": chunk.get("strategy"),
            "score": chunk.get("score"),
            "text": chunk.get("text"),
            "resolved_context": chunk.get("resolved_context"),
            "language": chunk.get("language"),
        })

    return {
        "transcript": result_ctx.transcript or result_ctx.query,
        "query": result_ctx.query,
        "answer": result_ctx.answer,
        "sources": sources,
        "timings_ms": result_ctx.timings_ms,
        "guardrail_flags": result_ctx.guardrail_flags,
        "detected_language": result_ctx.detected_language,
        "success": result_ctx.success,
        "errors": result_ctx.errors,
    }
