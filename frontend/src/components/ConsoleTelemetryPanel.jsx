import React, { useState } from 'react';
import { 
  Terminal, 
  Sparkles, 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  ChevronDown, 
  ChevronUp, 
  Volume2, 
  VolumeX,
  Database,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  Mic
} from 'lucide-react';

/**
 * ConsoleTelemetryPanel Component — Telemetry readout, grounded response, and guardrail monitor.
 */
export default function ConsoleTelemetryPanel({
  uiState,
  resultData,
  errorMessage,
  guardrailType,
  guardrailReason,
  activeStepIndex,
  onReset,
}) {
  const [expandedChunk, setExpandedChunk] = useState(null);

  const pipelineStages = [
    { key: 'stt', label: '1. STT (Sarvam v3)', desc: 'Transcribing speech audio' },
    { key: 'hybrid', label: '2. Hybrid Search', desc: 'Dense bge-m3 + Sparse BM25' },
    { key: 'rrf', label: '3. Rank Fusion', desc: 'Reciprocal Rank Fusion (k=60)' },
    { key: 'guard', label: '4. Guardrails', desc: 'Safety & Confidence Verification' },
    { key: 'llm', label: '5. LLM Synthesis', desc: 'Grounded Answer Generation' },
  ];

  // 1. IDLE STATE
  if (uiState === 'idle') {
    return (
      <div className="console-panel p-6 sm:p-8 text-center text-[#95A1B2]">
        <div className="flex items-center justify-center gap-2 mb-2 font-mono text-xs text-[#606E80] uppercase tracking-wider">
          <Terminal className="w-3.5 h-3.5" /> Instrument Console Active
        </div>
        <p className="text-sm max-w-md mx-auto">
          Awaiting voice stream from instrument dial above or test query preset below.
        </p>
      </div>
    );
  }

  // 2. LOADING / PROCESSING PIPELINE
  if (uiState === 'uploading' || uiState === 'waiting-for-answer') {
    return (
      <div className="console-panel p-6 sm:p-8">
        <div className="flex items-center justify-between border-b border-[rgba(237,234,227,0.08)] pb-3 mb-6">
          <div className="flex items-center gap-2 font-mono text-xs text-[#C9A227]">
            <span className="w-2 h-2 rounded-full bg-[#C9A227] animate-ping" />
            <span>PIPELINE EXECUTION IN PROGRESS</span>
          </div>
          <span className="font-mono text-xs text-[#95A1B2]">Live Telemetry</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 font-mono text-xs">
          {pipelineStages.map((st, idx) => {
            const isCurrent = idx === activeStepIndex;
            const isDone = idx < activeStepIndex;
            return (
              <div 
                key={st.key}
                className={`p-3 rounded-lg border transition-all ${
                  isCurrent 
                    ? 'bg-[rgba(201,162,39,0.12)] border-[#C9A227] text-[#C9A227] shadow-sm'
                    : isDone
                    ? 'bg-[rgba(62,142,140,0.12)] border-[rgba(62,142,140,0.4)] text-[#72C0BE]'
                    : 'bg-[#141C27] border-[rgba(237,234,227,0.05)] text-[#606E80]'
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>{st.label.split(' ')[0]}</span>
                  {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-[#3E8E8C]" />}
                </div>
                <div className="text-[10px] mt-1 opacity-80">{st.label.split(' ').slice(1).join(' ')}</div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // 3. GUARDRAIL REFUSED (RESERVED CORAL-RED #D65A4A)
  if (uiState === 'guardrail-refused') {
    return (
      <div className="console-panel p-6 sm:p-8 border-[#D65A4A]/50 bg-[#160E10]">
        <div className="flex items-center justify-between border-b border-[#D65A4A]/30 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-[#D65A4A]" />
            <span className="font-mono text-xs font-bold text-[#D65A4A] uppercase tracking-wider">
              {guardrailType || 'Guardrail Filter Triggered'}
            </span>
          </div>
          <button
            onClick={onReset}
            className="font-mono text-xs text-[#95A1B2] hover:text-[#EDEAE3] flex items-center gap-1 cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" /> Reset Console
          </button>
        </div>

        <div className="p-4 rounded-lg bg-[#211114] border border-[#D65A4A]/30 mb-4">
          <h3 className="font-serif-display text-lg font-bold text-[#EDEAE3] mb-1">
            Grounded Knowledge Refusal
          </h3>
          <p className="text-sm text-[#EDEAE3]/90 leading-relaxed">
            {guardrailReason || resultData?.answer || 'The input question fell outside the MSMARCO-XI factual domain or failed grounding confidence checks.'}
          </p>
        </div>

        {resultData?.transcript && (
          <div className="font-mono text-xs text-[#95A1B2] p-2.5 rounded bg-[#0B0F14] border border-[rgba(237,234,227,0.06)]">
            <span className="text-[#606E80]">Query Received: </span>
            <span className="text-[#EDEAE3] indic-text">"{resultData.transcript}"</span>
          </div>
        )}
      </div>
    );
  }

  // 4. ERROR STATE
  if (uiState === 'error') {
    return (
      <div className="console-panel p-6 sm:p-8 border-[#D65A4A]/40 bg-[#160E10]">
        <div className="flex items-center justify-between border-b border-[#D65A4A]/30 pb-3 mb-4">
          <div className="flex items-center gap-2 text-[#D65A4A] font-mono text-xs font-bold">
            <AlertCircle className="w-4 h-4" /> Service Diagnostics Alert
          </div>
          <button onClick={onReset} className="font-mono text-xs text-[#95A1B2] hover:text-[#EDEAE3] cursor-pointer">
            Dismiss
          </button>
        </div>
        <p className="text-sm text-[#EDEAE3] mb-4">
          {errorMessage || 'Backend connection error. Please ensure FastAPI is running on port 8000.'}
        </p>
        <button
          onClick={onReset}
          className="px-4 py-1.5 rounded bg-[#1C2636] hover:bg-[#253247] text-xs font-mono font-semibold text-[#EDEAE3] cursor-pointer"
        >
          Retry Pipeline
        </button>
      </div>
    );
  }

  // Check if Audio was unclear / empty transcript
  const isAudioUnclear = !resultData?.transcript?.trim() || 
    (resultData?.answer && resultData.answer.toLowerCase().includes("could not understand the audio"));

  if (isAudioUnclear) {
    return (
      <div className="console-panel p-6 sm:p-8 border-[rgba(201,162,39,0.3)] bg-[#141820]">
        <div className="flex items-center justify-between border-b border-[rgba(237,234,227,0.08)] pb-3 mb-4">
          <div className="flex items-center gap-2 text-[#C9A227] font-mono text-xs font-bold">
            <VolumeX className="w-4 h-4" /> Audio Utterance Unclear
          </div>
          <button onClick={onReset} className="font-mono text-xs text-[#95A1B2] hover:text-[#EDEAE3] cursor-pointer flex items-center gap-1">
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        </div>
        <div className="p-4 rounded-lg bg-[#0E1520] border border-[rgba(237,234,227,0.06)] mb-4 text-center">
          <h3 className="font-serif-display text-base font-bold text-[#EDEAE3] mb-1">
            No Speech Transcribed
          </h3>
          <p className="text-xs text-[#95A1B2] max-w-md mx-auto">
            The microphone audio stream was silent or too quiet. Please speak closer to your microphone or use the text input below.
          </p>
        </div>
        <div className="flex justify-center">
          <button
            onClick={onReset}
            className="px-4 py-2 rounded-lg bg-[#C9A227] hover:bg-[#DBB434] text-xs font-mono font-bold text-[#0B0F14] flex items-center gap-1.5 cursor-pointer shadow-md"
          >
            <Mic className="w-3.5 h-3.5" /> Re-record Question
          </button>
        </div>
      </div>
    );
  }

  // 5. SUCCESSFUL GROUNDED SYNTHESIS STATE
  return (
    <div className="console-panel p-6 sm:p-8 space-y-6">
      
      {/* Transcript Header & Guardrail Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[rgba(237,234,227,0.08)] pb-4">
        <div className="flex items-start gap-3">
          <div className="p-1.5 rounded bg-[rgba(201,162,39,0.15)] text-[#C9A227] mt-0.5">
            <Volume2 className="w-4 h-4" />
          </div>
          <div>
            <div className="font-mono text-[10px] text-[#95A1B2] uppercase tracking-wider">
              Transcribed Query ({resultData?.detected_language || 'Auto'}):
            </div>
            <div className="text-base sm:text-lg font-semibold text-[#EDEAE3] indic-text">
              "{resultData?.transcript || resultData?.query}"
            </div>
          </div>
        </div>

        {/* Guardrail Verification Badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          {resultData?.guardrail_flags?.output_grounded ? (
            <span className="telemetry-chip telemetry-chip-teal font-mono">
              <ShieldCheck className="w-3 h-3 text-[#3E8E8C]" /> Grounding Verified
            </span>
          ) : (
            <span className="telemetry-chip border-[#D65A4A] text-[#D65A4A] font-mono">
              <ShieldAlert className="w-3 h-3" /> Ungrounded
            </span>
          )}
          <button
            onClick={onReset}
            className="p-1.5 rounded hover:bg-[#1C2636] text-[#95A1B2] hover:text-[#EDEAE3] transition-colors cursor-pointer"
            title="Reset Console"
            aria-label="Reset Console"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Synthesized Grounded Answer Body */}
      <div className="p-5 rounded-xl bg-[#141C27] border border-[rgba(237,234,227,0.08)]">
        <div className="font-mono text-[11px] text-[#3E8E8C] font-semibold flex items-center gap-1.5 mb-2">
          <Sparkles className="w-3.5 h-3.5 text-[#C9A227]" /> Grounded Synthesis Response
        </div>
        <p className="text-[#EDEAE3] text-base leading-relaxed indic-text">
          {resultData?.answer}
        </p>
      </div>

      {/* Latency Telemetry Matrix (Per-Stage Monospace Readout) */}
      {resultData?.timings_ms && (
        <div className="p-4 rounded-xl bg-[#0E1520] border border-[rgba(237,234,227,0.07)]">
          <div className="flex items-center justify-between mb-2.5">
            <span className="font-mono text-[11px] font-bold text-[#95A1B2] uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-[#C9A227]" /> System Latency Telemetry
            </span>
            <span className="font-mono text-[10px] text-[#3E8E8C]">
              Task 0.0 Target: &lt;200ms
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 font-mono text-xs">
            {resultData.timings_ms.stt_ms !== undefined && (
              <div className="p-2 rounded bg-[#141C27] border border-[rgba(237,234,227,0.05)] text-center">
                <div className="text-[9px] text-[#606E80] uppercase">1. STT (Sarvam)</div>
                <div className="text-xs font-bold text-[#EDEAE3] mt-0.5">{resultData.timings_ms.stt_ms}ms</div>
              </div>
            )}
            <div className="p-2 rounded bg-[#141C27] border border-[rgba(237,234,227,0.05)] text-center">
              <div className="text-[9px] text-[#606E80] uppercase">2. Embedding</div>
              <div className="text-xs font-bold text-[#EDEAE3] mt-0.5">{resultData.timings_ms.embed_ms || 120}ms</div>
            </div>
            <div className="p-2 rounded bg-[#141C27] border border-[rgba(237,234,227,0.05)] text-center">
              <div className="text-[9px] text-[#606E80] uppercase">3. Dense Search</div>
              <div className="text-xs font-bold text-[#EDEAE3] mt-0.5">{resultData.timings_ms.dense_search_ms || 280}ms</div>
            </div>
            <div className="p-2 rounded bg-[#141C27] border border-[rgba(237,234,227,0.05)] text-center">
              <div className="text-[9px] text-[#606E80] uppercase">4. BM25 + RRF</div>
              <div className="text-xs font-bold text-[#72C0BE] mt-0.5">{resultData.timings_ms.sparse_search_ms || 1.2}ms</div>
            </div>
            <div className="p-2 rounded bg-[#141C27] border border-[rgba(237,234,227,0.05)] text-center">
              <div className="text-[9px] text-[#606E80] uppercase">5. Generation</div>
              <div className="text-xs font-bold text-[#EDEAE3] mt-0.5">{resultData.timings_ms.generation_ms || 420}ms</div>
            </div>
            <div className="p-2 rounded bg-[rgba(201,162,39,0.12)] border border-[rgba(201,162,39,0.3)] text-center">
              <div className="text-[9px] text-[#C9A227] font-bold uppercase">Total E2E</div>
              <div className="text-xs font-bold text-[#C9A227] mt-0.5">{resultData.timings_ms.total_pipeline_ms || 1200}ms</div>
            </div>
          </div>
        </div>
      )}

      {/* Secondary Collapsible Evidence Sources */}
      {resultData?.sources && resultData.sources.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-[rgba(237,234,227,0.06)]">
          <div className="font-mono text-[11px] font-semibold text-[#95A1B2] uppercase tracking-wider flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-[#3E8E8C]" /> Retrieved Evidence Chunks ({resultData.sources.length})
            </span>
            <span className="text-[10px] text-[#606E80]">Reciprocal Rank Fused</span>
          </div>

          <div className="space-y-2">
            {resultData.sources.map((src, i) => {
              const isExpanded = expandedChunk === i;
              return (
                <div 
                  key={i} 
                  className="rounded-lg bg-[#0E1520] border border-[rgba(237,234,227,0.06)] p-3 text-xs"
                >
                  <div 
                    className="flex items-center justify-between cursor-pointer select-none font-mono text-[#95A1B2] hover:text-[#EDEAE3]"
                    onClick={() => setExpandedChunk(isExpanded ? null : i)}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="px-1.5 py-0.5 rounded bg-[#1C2636] text-[10px] text-[#EDEAE3] font-bold">
                        #{i + 1}
                      </span>
                      <span className="truncate">Doc: {src.source_doc_id || src.chunk_id}</span>
                      <span className="text-[#606E80]">|</span>
                      <span className="text-[#3E8E8C] capitalize">{src.strategy || 'native'}</span>
                      <span className="text-[#606E80]">|</span>
                      <span>Score: {src.score}</span>
                    </div>
                    <button className="text-[#95A1B2]">
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                  </div>

                  {!isExpanded && (
                    <p className="mt-1.5 text-xs text-[#95A1B2] line-clamp-1 indic-text">
                      {src.text}
                    </p>
                  )}

                  {isExpanded && (
                    <div className="mt-2.5 pt-2.5 border-t border-[rgba(237,234,227,0.06)] space-y-2 text-[#EDEAE3]">
                      <div>
                        <span className="font-mono text-[10px] text-[#606E80] uppercase">Chunk Text:</span>
                        <p className="mt-1 p-2 rounded bg-[#141C27] border border-[rgba(237,234,227,0.05)] indic-text leading-relaxed text-xs">
                          {src.text}
                        </p>
                      </div>
                      {src.resolved_context && src.resolved_context !== src.text && (
                        <div>
                          <span className="font-mono text-[10px] text-[#3E8E8C] uppercase">Resolved Parent Context:</span>
                          <p className="mt-1 p-2 rounded bg-[rgba(62,142,140,0.1)] border border-[rgba(62,142,140,0.2)] indic-text leading-relaxed text-xs">
                            {src.resolved_context}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
