import React, { useState, useRef, useEffect } from 'react';
import { 
  Mic, 
  Square, 
  Loader2, 
  Sparkles, 
  ShieldCheck, 
  ShieldAlert, 
  Clock, 
  Layers, 
  Volume2, 
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ChevronDown,
  ChevronUp,
  Send,
  HelpCircle
} from 'lucide-react';
import { askQuestion, askTextQuestion } from '../api/client';

/**
 * VoiceQA Component — Connected Live Multilingual Voice & Text RAG Console.
 * Orchestrates browser MediaRecorder capture -> Backend /api/ask -> Grounded UI Synthesis.
 */
export default function VoiceQA({ selectedLanguage = 'hin', selectedStrategy = 'passage_native' }) {
  // UI States: 'idle' | 'recording' | 'uploading' | 'waiting-for-answer' | 'showing-answer' | 'error' | 'guardrail-refused'
  const [uiState, setUiState] = useState('idle');
  const [activeStepMessage, setActiveStepMessage] = useState('');
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [resultData, setResultData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [guardrailReason, setGuardrailReason] = useState('');
  const [expandedSource, setExpandedSource] = useState(null);
  const [textInput, setTextInput] = useState('');

  // Audio Recording Refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);

  // Clean up timer & tracks on unmount
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // --- Browser Microphone Recording Handlers ---
  const startRecording = async () => {
    setErrorMessage('');
    setGuardrailReason('');
    audioChunksRef.current = [];
    setRecordingDuration(0);

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Microphone access is not supported in this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        // Release mic hardware tracks
        stream.getTracks().forEach(track => track.stop());
        handleAudioCaptured(audioBlob);
      };

      mediaRecorder.start();
      setUiState('recording');

      // Start elapsed timer
      timerIntervalRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Microphone error:', err);
      setErrorMessage(err.message || 'Could not access microphone. Please check permissions.');
      setUiState('error');
    }
  };

  const stopRecording = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  // --- Process Audio via Real Backend API ---
  const handleAudioCaptured = async (audioBlob) => {
    setUiState('uploading');
    setActiveStepMessage('Uploading voice recording to backend...');

    try {
      // Transition to processing state
      setTimeout(() => {
        setUiState('waiting-for-answer');
        setActiveStepMessage('Transcribing speech & searching MSMARCO-XI...');
      }, 400);

      const response = await askQuestion(audioBlob, selectedLanguage, selectedStrategy);
      handlePipelineResponse(response);
    } catch (err) {
      console.error('Failed to process voice query:', err);
      setErrorMessage(err.message || 'Error communicating with backend service. Please ensure the backend is running.');
      setUiState('error');
    }
  };

  // --- Process Text Query via Real Backend API ---
  const handleTextSubmit = async (e) => {
    if (e) e.preventDefault();
    const clean = textInput.trim();
    if (!clean) return;

    setUiState('waiting-for-answer');
    setActiveStepMessage('Searching hybrid vector index & validating grounding...');
    setErrorMessage('');
    setGuardrailReason('');

    try {
      const response = await askTextQuestion(clean, selectedLanguage, selectedStrategy);
      handlePipelineResponse(response);
      setTextInput('');
    } catch (err) {
      console.error('Failed to process text query:', err);
      setErrorMessage(err.message || 'Error communicating with backend service.');
      setUiState('error');
    }
  };

  // --- Common Response Evaluation & Guardrail Interpretation ---
  const handlePipelineResponse = (response) => {
    setResultData(response);

    const flags = response.guardrail_flags || {};

    // Check if any guardrail fired
    if (flags.input_safe === false) {
      setGuardrailReason('Safety Guardrail: This question was flagged as containing unsafe or prohibited content.');
      setUiState('guardrail-refused');
      return;
    }

    if (flags.input_offtopic === true) {
      setGuardrailReason('Topicality Guardrail: This question appears to be outside the general knowledge domain of the MSMARCO-XI dataset.');
      setUiState('guardrail-refused');
      return;
    }

    if (flags.retrieval_confident === false && (!response.sources || response.sources.length === 0)) {
      setGuardrailReason('Confidence Guardrail: No sufficiently confident evidence passages were found in the knowledge base to answer this question factually.');
      setUiState('guardrail-refused');
      return;
    }

    if (flags.output_grounded === false) {
      setGuardrailReason('Grounding Guardrail: The synthesized answer could not be factually verified against the retrieved context passages.');
      setUiState('guardrail-refused');
      return;
    }

    // Standard successful grounded synthesis
    setUiState('showing-answer');
  };

  const resetToIdle = () => {
    setUiState('idle');
    setResultData(null);
    setErrorMessage('');
    setGuardrailReason('');
    setRecordingDuration(0);
    setActiveStepMessage('');
  };

  // Format seconds to MM:SS
  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-4">
      {/* Main Glassmorphic QA Card */}
      <div className="glass-panel p-6 sm:p-10 relative overflow-hidden">
        
        {/* State 1: IDLE */}
        {uiState === 'idle' && (
          <div className="text-center py-4 sm:py-6">
            <div className="mb-6 flex justify-center">
              <button
                id="start-record-btn"
                onClick={startRecording}
                className="mic-btn-idle w-24 h-24 sm:w-28 sm:h-28 rounded-full flex flex-col items-center justify-center text-white cursor-pointer group shadow-2xl"
                aria-label="Start voice recording"
              >
                <Mic className="w-10 h-10 sm:w-12 sm:h-12 group-hover:scale-110 transition-transform" />
              </button>
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold mb-2 tracking-tight">
              Tap Microphone to Speak
            </h2>
            <p className="text-gray-400 text-sm sm:text-base max-w-md mx-auto mb-6">
              Ask in <span className="text-indigo-400 font-semibold">{selectedLanguage === 'hin' ? 'Hindi' : selectedLanguage === 'tam' ? 'Tamil' : 'English'}</span>. We transcribe with Sarvam AI, retrieve grounded MSMARCO evidence, and answer factually.
            </p>

            {/* Quick Text Input Option */}
            <form onSubmit={handleTextSubmit} className="max-w-md mx-auto mb-6 flex items-center gap-2">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder={selectedLanguage === 'hin' ? 'या यहाँ हिंदी में टाइप करें...' : selectedLanguage === 'tam' ? 'அல்லது தமிழில் தட்டச்சு செய்க...' : 'Or type a question here...'}
                className="flex-1 px-4 py-2.5 rounded-xl bg-gray-800/80 border border-gray-700 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 indic-text"
              />
              <button
                type="submit"
                disabled={!textInput.trim()}
                className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white transition-colors cursor-pointer"
                aria-label="Submit text question"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>

            {/* Active System Badges */}
            <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
              <span className="badge-telemetry">
                <Layers className="w-3.5 h-3.5" /> Strategy: {selectedStrategy}
              </span>
              <span className="badge-telemetry">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Multi-tier Guardrails Active
              </span>
            </div>
          </div>
        )}

        {/* State 2: RECORDING */}
        {uiState === 'recording' && (
          <div className="text-center py-8">
            <div className="mb-6 flex justify-center">
              <button
                id="stop-record-btn"
                onClick={stopRecording}
                className="mic-btn-recording w-24 h-24 sm:w-28 sm:h-28 rounded-full flex flex-col items-center justify-center text-white cursor-pointer shadow-2xl"
                aria-label="Stop recording"
              >
                <Square className="w-10 h-10 fill-current" />
              </button>
            </div>

            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 font-mono text-sm font-semibold mb-4">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
              Recording: {formatTimer(recordingDuration)}
            </div>

            {/* Animated Audio Waveform */}
            <div className="flex items-center justify-center gap-1.5 h-12 mb-4">
              {[0.2, 0.4, 0.6, 0.8, 1.0, 0.7, 0.5, 0.3, 0.6, 0.9, 0.4, 0.2].map((delay, i) => (
                <div 
                  key={i} 
                  className="wave-bar" 
                  style={{ animationDelay: `${delay}s`, height: `${12 + (i % 4) * 8}px` }} 
                />
              ))}
            </div>

            <p className="text-gray-300 text-sm">
              Speak your question clearly. Tap the red button when finished.
            </p>
          </div>
        )}

        {/* State 3: UPLOADING & WAITING */}
        {(uiState === 'uploading' || uiState === 'waiting-for-answer') && (
          <div className="text-center py-12">
            <div className="flex justify-center mb-6">
              <div className="w-20 h-20 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-lg shadow-indigo-500/20">
                <Loader2 className="w-10 h-10 animate-spin" />
              </div>
            </div>

            <h3 className="text-xl sm:text-2xl font-bold mb-2">
              {activeStepMessage || 'Processing Voice RAG Pipeline...'}
            </h3>
            <p className="text-xs text-gray-400 mb-6 max-w-sm mx-auto">
              Executing STT transcription, hybrid vector retrieval, and factual grounding checks.
            </p>

            {/* Pipeline Stage Indicators */}
            <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto text-xs text-gray-400">
              <span className={`px-3 py-1 rounded-full border ${uiState === 'uploading' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 animate-pulse' : 'bg-gray-800 border-gray-700 text-emerald-400'}`}>
                1. Sarvam AI STT
              </span>
              <span className={`px-3 py-1 rounded-full border ${uiState === 'waiting-for-answer' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 animate-pulse' : 'bg-gray-800 border-gray-700'}`}>
                2. Qdrant Hybrid Search & RRF
              </span>
              <span className="px-3 py-1 rounded-full bg-gray-800 border border-gray-700">
                3. Grounded Synthesis
              </span>
            </div>
          </div>
        )}

        {/* State 4: SHOWING ANSWER */}
        {uiState === 'showing-answer' && resultData && (
          <div className="space-y-6">
            {/* Query Header */}
            <div className="p-4 rounded-xl bg-gray-800/40 border border-gray-700/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
                  <Volume2 className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs text-gray-400 font-medium">
                    Question ({resultData.detected_language || selectedLanguage}):
                  </div>
                  <div className="text-base sm:text-lg font-semibold text-white indic-text">
                    "{resultData.transcript || resultData.query}"
                  </div>
                </div>
              </div>
              <button
                onClick={resetToIdle}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gray-700/50 hover:bg-gray-700 text-gray-300 transition-colors self-start sm:self-auto cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Ask Another
              </button>
            </div>

            {/* Grounded Answer Card */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-gray-900/60 border border-indigo-500/30 shadow-xl">
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-indigo-300 font-semibold text-sm">
                  <Sparkles className="w-4 h-4 text-indigo-400" /> Grounded Answer
                </div>
                {resultData.guardrail_flags?.output_grounded && (
                  <span className="badge-guardrail-pass text-xs font-semibold px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Factual Grounding Verified
                  </span>
                )}
              </div>
              <p className="text-gray-100 text-base sm:text-lg leading-relaxed indic-text">
                {resultData.answer}
              </p>
            </div>

            {/* Latency Telemetry Badges */}
            {resultData.timings_ms && (
              <div className="p-4 rounded-xl bg-gray-900/60 border border-gray-800">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-indigo-400" /> Latency Telemetry Breakdown (Live Execution)
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                  {resultData.timings_ms.stt_ms !== undefined && resultData.timings_ms.stt_ms > 0 && (
                    <span className="badge-telemetry">
                      STT: <strong className="text-white ml-0.5">{resultData.timings_ms.stt_ms}ms</strong>
                    </span>
                  )}
                  {resultData.timings_ms.dense_search_ms !== undefined && (
                    <span className="badge-telemetry">
                      Dense Search: <strong className="text-white ml-0.5">{resultData.timings_ms.dense_search_ms}ms</strong>
                    </span>
                  )}
                  {resultData.timings_ms.sparse_search_ms !== undefined && (
                    <span className="badge-telemetry">
                      BM25 Sparse: <strong className="text-white ml-0.5">{resultData.timings_ms.sparse_search_ms}ms</strong>
                    </span>
                  )}
                  {resultData.timings_ms.retrieval_ms !== undefined && (
                    <span className="badge-telemetry">
                      Retrieval Total: <strong className="text-white ml-0.5">{resultData.timings_ms.retrieval_ms}ms</strong>
                    </span>
                  )}
                  {resultData.timings_ms.generation_ms !== undefined && (
                    <span className="badge-telemetry">
                      LLM Generation: <strong className="text-white ml-0.5">{resultData.timings_ms.generation_ms}ms</strong>
                    </span>
                  )}
                  {resultData.timings_ms.retrieval_to_output_ms !== undefined && (
                    <span className="badge-telemetry bg-indigo-600/20 text-indigo-200 border-indigo-400/40">
                      Retrieval-to-Output: <strong className="text-white ml-0.5">{resultData.timings_ms.retrieval_to_output_ms}ms</strong>
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Source Citations Accordion */}
            {resultData.sources && resultData.sources.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-indigo-400" /> Evidence Passages ({resultData.sources.length} Retrieved Chunks)
                </div>
                <div className="space-y-2">
                  {resultData.sources.map((src, i) => {
                    const isExpanded = expandedSource === i;
                    return (
                      <div 
                        key={i} 
                        className="rounded-xl bg-gray-800/30 border border-gray-700/50 p-3.5 hover:border-gray-600 transition-colors"
                      >
                        <div 
                          className="flex items-center justify-between cursor-pointer select-none"
                          onClick={() => setExpandedSource(isExpanded ? null : i)}
                        >
                          <div className="flex items-center gap-2 text-xs text-gray-300 font-medium">
                            <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-xs font-semibold">
                              {i + 1}
                            </span>
                            <span>Doc: {src.source_doc_id || src.chunk_id}</span>
                            <span className="text-gray-500">|</span>
                            <span className="text-indigo-400 capitalize">{src.strategy || 'native'}</span>
                            <span className="text-gray-500">|</span>
                            <span className="text-gray-400">Score: {src.score}</span>
                          </div>
                          <button className="text-gray-400 hover:text-gray-200">
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>

                        {/* Collapsed Snippet */}
                        {!isExpanded && (
                          <div className="mt-1.5 text-xs text-gray-400 line-clamp-1 indic-text">
                            {src.text}
                          </div>
                        )}

                        {/* Expanded Full Context */}
                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-gray-700/40 text-xs text-gray-300 space-y-2">
                            <div>
                              <strong className="text-gray-400">Matched Chunk:</strong>
                              <p className="mt-1 p-2 rounded bg-gray-900/50 border border-gray-800 indic-text leading-relaxed">
                                {src.text}
                              </p>
                            </div>
                            {src.resolved_context && src.resolved_context !== src.text && (
                              <div>
                                <strong className="text-indigo-400">Resolved Parent Passage:</strong>
                                <p className="mt-1 p-2 rounded bg-indigo-950/30 border border-indigo-900/40 indic-text leading-relaxed">
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

            {/* Bottom Action Button */}
            <div className="pt-4 flex justify-center">
              <button
                onClick={resetToIdle}
                className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition-all shadow-lg hover:shadow-indigo-500/25 flex items-center gap-2 cursor-pointer"
              >
                <Mic className="w-4 h-4" /> Ask Another Question
              </button>
            </div>
          </div>
        )}

        {/* State 5: ERROR */}
        {uiState === 'error' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto mb-4">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Service Error</h3>
            <p className="text-gray-300 text-sm max-w-md mx-auto mb-6">
              {errorMessage || 'Unable to complete voice request. Please ensure the backend server is running.'}
            </p>
            <button
              onClick={resetToIdle}
              className="px-5 py-2.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-sm font-semibold transition-colors cursor-pointer"
            >
              Try Again
            </button>
          </div>
        )}

        {/* State 6: GUARDRAIL REFUSED */}
        {uiState === 'guardrail-refused' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mx-auto mb-4 shadow-lg shadow-amber-500/20">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Guardrail Refusal</h3>
            <p className="text-gray-300 text-sm max-w-md mx-auto mb-6">
              {guardrailReason || resultData?.answer || 'I cannot answer this query because it fell outside the scope of the knowledge base or failed grounding verification.'}
            </p>

            {/* Display Question for Context */}
            {resultData?.transcript && (
              <div className="mb-6 p-3 rounded-xl bg-gray-800/50 border border-gray-700 max-w-md mx-auto text-xs text-gray-300 indic-text">
                <strong>Question asked:</strong> "{resultData.transcript}"
              </div>
            )}

            <button
              onClick={resetToIdle}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors cursor-pointer"
            >
              Ask a Valid Knowledge Question
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
