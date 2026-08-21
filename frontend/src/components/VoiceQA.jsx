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
  ChevronUp
} from 'lucide-react';

/**
 * VoiceQA Component — Voice-Enabled Multilingual RAG Interactive Console.
 * Supports browser microphone capture, rich pipeline states, telemetry badges, and source citations.
 */
export default function VoiceQA({ selectedLanguage = 'hin', selectedStrategy = 'passage_native' }) {
  // UI Pipeline States: 'idle' | 'recording' | 'uploading' | 'waiting-for-answer' | 'showing-answer' | 'error' | 'guardrail-refused'
  const [uiState, setUiState] = useState('idle');
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [resultData, setResultData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [expandedSource, setExpandedSource] = useState(null);

  // Audio Recording Refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);

  // Clean up timer on unmount
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
        // Stop all tracks to release mic hardware
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

  // --- Audio Processing (Task 6.1 Stub Implementation) ---
  const handleAudioCaptured = async (audioBlob) => {
    setUiState('uploading');

    // Simulate upload delay
    setTimeout(() => {
      setUiState('waiting-for-answer');
      
      // Simulate pipeline synthesis delay (STT -> Retrieve -> Generate)
      setTimeout(() => {
        // Stub mock response for Task 6.1 UI state validation
        const mockResponse = {
          transcript: selectedLanguage === 'tam' ? 'பொட்டாசியம் குறைந்த உணவுகள் என்ன?' : 'कॉर्पोरेशन क्या है?',
          query: selectedLanguage === 'tam' ? 'பொட்டாசியம் குறைந்த உணவுகள் என்ன?' : 'कॉर्पोरेशन क्या है?',
          detected_language: selectedLanguage === 'tam' ? 'ta-IN' : 'hi-IN',
          answer: selectedLanguage === 'tam' 
            ? 'பொட்டாசியம் குறைந்த உணவுகளில் ஆப்பிள், திராட்சை, பெர்ரி, வெள்ளரிக்காய், மற்றும் முட்டைக்கோஸ் ஆகியவை அடங்கும்.'
            : 'निगम (Corporation) एक ऐसी कंपनी या लोगों का समूह है जो कानून की नजर में एक एकल इकाई (Single Legal Entity) के रूप में कार्य करने के लिए अधिकृत होता है।',
          sources: [
            {
              chunk_id: 'msmarco_hin_p1',
              source_doc_id: '1102432_p1',
              strategy: selectedStrategy,
              score: 0.0328,
              text: 'एक कंपनी एक विशिष्ट देश में निगमित होती है, अक्सर उस देश के एक छोटे उपसमूह में कानून के तहत मान्यता प्राप्त होती है।',
              resolved_context: 'एक निगम एक कंपनी या लोगों का समूह होता है जो एक एकल इकाई के रूप में कार्य करने के लिए अधिकृत होता है और कानून में इस प्रकार से मान्यता प्राप्त होती है।',
              language: selectedLanguage,
            },
            {
              chunk_id: 'msmarco_hin_p2',
              source_doc_id: '1102432_p4',
              strategy: selectedStrategy,
              score: 0.0295,
              text: 'निगम के शेयरधारक कंपनी के ऋणों के लिए व्यक्तिगत रूप से उत्तरदायी नहीं होते हैं।',
              resolved_context: 'निगम के शेयरधारक कंपनी के ऋणों के लिए व्यक्तिगत रूप से उत्तरदायी नहीं होते हैं (सीमित देयता)।',
              language: selectedLanguage,
            }
          ],
          timings_ms: {
            stt_ms: 780.0,
            embed_ms: 120.5,
            dense_search_ms: 280.2,
            sparse_search_ms: 1.2,
            fusion_ms: 0.02,
            retrieval_ms: 410.0,
            generation_ms: 440.5,
            ttft_ms: 320.0,
            retrieval_to_output_ms: 850.5,
            total_pipeline_ms: 1630.5,
          },
          guardrail_flags: {
            input_safe: true,
            input_offtopic: false,
            retrieval_confident: true,
            output_grounded: true,
          },
          success: true,
        };

        setResultData(mockResponse);
        setUiState('showing-answer');
      }, 1200);
    }, 800);
  };

  const resetToIdle = () => {
    setUiState('idle');
    setResultData(null);
    setErrorMessage('');
    setRecordingDuration(0);
  };

  // Format seconds to MM:SS
  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-8">
      {/* Main Glassmorphic QA Card */}
      <div className="glass-panel p-6 sm:p-10 relative overflow-hidden">
        
        {/* State 1: IDLE */}
        {uiState === 'idle' && (
          <div className="text-center py-8">
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
              Tap to Ask in Voice
            </h2>
            <p className="text-gray-400 text-sm sm:text-base max-w-md mx-auto mb-6">
              Ask any question in <span className="text-indigo-400 font-semibold">{selectedLanguage === 'hin' ? 'Hindi' : selectedLanguage === 'tam' ? 'Tamil' : 'English'}</span>. We transcribe, retrieve grounded MSMARCO evidence, and answer in real-time.
            </p>

            {/* Strategy & Language Pills */}
            <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
              <span className="badge-telemetry">
                <Layers className="w-3.5 h-3.5" /> Strategy: {selectedStrategy}
              </span>
              <span className="badge-telemetry">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Grounding Guardrails Active
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
              Speak clearly into your microphone. Tap the square button when done.
            </p>
          </div>
        )}

        {/* State 3: UPLOADING & WAITING */}
        {(uiState === 'uploading' || uiState === 'waiting-for-answer') && (
          <div className="text-center py-12">
            <div className="flex justify-center mb-6">
              <div className="w-20 h-20 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <Loader2 className="w-10 h-10 animate-spin" />
              </div>
            </div>

            <h3 className="text-xl sm:text-2xl font-bold mb-3">
              {uiState === 'uploading' ? 'Uploading Audio Payload...' : 'Synthesizing Grounded Answer...'}
            </h3>

            {/* Pipeline Step Indicators */}
            <div className="flex flex-wrap justify-center gap-2 max-w-lg mx-auto text-xs text-gray-400">
              <span className={`px-3 py-1 rounded-full border ${uiState === 'uploading' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' : 'bg-gray-800 border-gray-700 text-emerald-400'}`}>
                ✓ Speech-to-Text (Sarvam v3)
              </span>
              <span className={`px-3 py-1 rounded-full border ${uiState === 'waiting-for-answer' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 animate-pulse' : 'bg-gray-800 border-gray-700'}`}>
                ⚙ Hybrid Search & RRF
              </span>
              <span className="px-3 py-1 rounded-full bg-gray-800 border border-gray-700">
                ⚙ Grounding Guardrail
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
                  <div className="text-xs text-gray-400 font-medium">Your Question ({resultData.detected_language || 'Voice'}):</div>
                  <div className="text-base sm:text-lg font-semibold text-white indic-text">
                    "{resultData.transcript}"
                  </div>
                </div>
              </div>
              <button
                onClick={resetToIdle}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gray-700/50 hover:bg-gray-700 text-gray-300 transition-colors self-start sm:self-auto cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Ask Again
              </button>
            </div>

            {/* Grounded Answer Card */}
            <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-gray-900/60 border border-indigo-500/30 shadow-xl">
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2 text-indigo-300 font-semibold text-sm">
                  <Sparkles className="w-4 h-4 text-indigo-400" /> Grounded Synthesis
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
                  <Clock className="w-3.5 h-3.5 text-indigo-400" /> Latency Telemetry Breakdown (P50 Benchmarked)
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="badge-telemetry">
                    STT: <strong className="text-white ml-0.5">{resultData.timings_ms.stt_ms || 0}ms</strong>
                  </span>
                  <span className="badge-telemetry">
                    Dense Search: <strong className="text-white ml-0.5">{resultData.timings_ms.dense_search_ms || 0}ms</strong>
                  </span>
                  <span className="badge-telemetry">
                    Sparse BM25: <strong className="text-white ml-0.5">{resultData.timings_ms.sparse_search_ms || 0}ms</strong>
                  </span>
                  <span className="badge-telemetry">
                    Retrieval Total: <strong className="text-white ml-0.5">{resultData.timings_ms.retrieval_ms || 0}ms</strong>
                  </span>
                  <span className="badge-telemetry">
                    LLM Synthesis: <strong className="text-white ml-0.5">{resultData.timings_ms.generation_ms || 0}ms</strong>
                  </span>
                  <span className="badge-telemetry bg-indigo-600/20 text-indigo-200 border-indigo-400/40">
                    Retrieval-to-Output: <strong className="text-white ml-0.5">{resultData.timings_ms.retrieval_to_output_ms || 0}ms</strong>
                  </span>
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
                            <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-xs">
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
                              <strong className="text-gray-400">Matched Chunk Text:</strong>
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

            {/* Bottom Action */}
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
            <h3 className="text-xl font-bold text-white mb-2">Something went wrong</h3>
            <p className="text-gray-400 text-sm max-w-md mx-auto mb-6">
              {errorMessage || 'Unable to complete voice request. Please check your network or try again.'}
            </p>
            <button
              onClick={resetToIdle}
              className="px-5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-sm font-semibold transition-colors cursor-pointer"
            >
              Try Again
            </button>
          </div>
        )}

        {/* State 6: GUARDRAIL REFUSED */}
        {uiState === 'guardrail-refused' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mx-auto mb-4">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Guardrail Refusal</h3>
            <p className="text-gray-300 text-sm max-w-md mx-auto mb-6">
              I cannot answer this query because it fell outside the scope of the knowledge base or was flagged by content safety rules.
            </p>
            <button
              onClick={resetToIdle}
              className="px-5 py-2 rounded-xl bg-gray-800 hover:bg-gray-700 text-white text-sm font-semibold transition-colors cursor-pointer"
            >
              Ask a Valid Question
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
