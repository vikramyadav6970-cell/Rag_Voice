"""Unit tests for backend/src/harness.py."""

import pytest
from backend.src.harness import (
    PipelineContext,
    RAGPipelineHarness,
    run_rag_pipeline,
)


@pytest.mark.asyncio
async def test_harness_text_pipeline_execution():
    """Verify harness executes retrieve -> generate -> return_result on text query."""
    res = await run_rag_pipeline(query="कॉर्पोरेशन क्या है?", language_hint="hin", top_k=2)
    assert res["success"] is True
    assert len(res["answer"]) > 0
    assert "timings_ms" in res
    assert "total_pipeline_ms" in res["timings_ms"]
    assert "retrieval_ms" in res["timings_ms"]
    assert "generation_ms" in res["timings_ms"]
    assert "guardrail_flags" in res


@pytest.mark.asyncio
async def test_harness_empty_audio_handling():
    """Verify harness handles empty audio input gracefully without throwing unhandled exceptions."""
    res = await run_rag_pipeline(audio_bytes=b"")
    assert "timings_ms" in res


@pytest.mark.asyncio
async def test_harness_guardrail_hook_integration():
    """Verify pluggable guardrail hooks intercept unsafe queries."""
    custom_harness = RAGPipelineHarness()

    async def mock_unsafe_guard(query: str):
        return {"input_safe": False, "input_offtopic": False}

    custom_harness.input_guardrail_hook = mock_unsafe_guard

    ctx = PipelineContext(query="prohibited unsafe query")
    res_ctx = await custom_harness.execute(ctx)
    assert res_ctx.guardrail_flags["input_safe"] is False
    assert "unsafe" in res_ctx.answer.lower()
    assert res_ctx.stop_early is True
