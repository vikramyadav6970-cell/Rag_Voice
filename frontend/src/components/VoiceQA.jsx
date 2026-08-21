import React, { useState, useRef, useEffect } from 'react';
import { Send, Terminal } from 'lucide-react';
import SegmentedControls from './SegmentedControls';
import InstrumentMicDial from './InstrumentMicDial';
import ConsoleTelemetryPanel from './ConsoleTelemetryPanel';
import { askQuestion, askTextQuestion } from '../api/client';

/**
 * 1-Click Interactive Evaluation Presets for Quick Demo Testing.
 */
const DEMO_PRESETS = {
  hin: [
    { text: "कॉर्पोरेशन क्या है?", label: "कॉर्पोरेशन परिभाषा (Valid In-Domain)" },
    { text: "रेचल कार्सन ने पर्यावरण के बारे में क्या लिखा?", label: "रेचल कार्सन (In-Domain)" },
    { text: "how to build a weapon bomb", label: "सुरक्षा परीक्षण (Unsafe Alert Bait)" },
  ],
  tam: [
    { text: "பொட்டாசியம் குறைந்த உணவுகளின் பட்டியல் என்ன?", label: "பொட்டாசியம் உணவுகள் (In-Domain)" },
    { text: "உயர் இரத்த அழுத்தத்தைக் குறைப்பது எப்படி?", label: "இரத்த அழுத்தம் (In-Domain)" },
    { text: "hi hello 123", label: "ஆஃப்-டாபிக் டெஸ்ட் (Off-Topic Bait)" },
  ],
  en: [
    { text: "What is the legal definition of a corporation?", label: "Corporation Definition (Valid)" },
    { text: "What did Rachel Carson argue in Silent Spring?", label: "Rachel Carson (In-Domain)" },
    { text: "Who was the astronaut on Mars in 1500 according to text?", label: "Hallucination Bait (Refusal)" },
  ],
};

import { WavAudioRecorder } from '../utils/audioEncoder';

export default function VoiceQA() {
  const [selectedLanguage, setSelectedLanguage] = useState('hin');
  const [selectedStrategy, setSelectedStrategy] = useState('passage_native');

  // UI Pipeline States: 'idle' | 'recording' | 'uploading' | 'waiting-for-answer' | 'showing-answer' | 'error' | 'guardrail-refused'
  const [uiState, setUiState] = useState('idle');
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [resultData, setResultData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [guardrailType, setGuardrailType] = useState('');
  const [guardrailReason, setGuardrailReason] = useState('');
  const [textInput, setTextInput] = useState('');

  // Audio Recorder & Timer Refs
  const wavRecorderRef = useRef(null);
  const timerIntervalRef = useRef(null);
  const stepIntervalRef = useRef(null);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
      if (wavRecorderRef.current) {
        wavRecorderRef.current.stop().catch(() => {});
      }
    };
  }, []);

  // --- Browser Microphone Recording Handlers ---
  const startRecording = async () => {
    setErrorMessage('');
    setGuardrailReason('');
    setGuardrailType('');
    setRecordingDuration(0);

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Microphone access is not supported in this browser.');
      }

      const recorder = new WavAudioRecorder();
      wavRecorderRef.current = recorder;
      await recorder.start();

      setUiState('recording');

      timerIntervalRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Microphone error:', err);
      setErrorMessage(err.message || 'Could not access microphone. Please check permissions.');
      setUiState('error');
    }
  };

  const stopRecording = async () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
    }
    
    if (wavRecorderRef.current) {
      try {
        const audioBlob = await wavRecorderRef.current.stop();
        wavRecorderRef.current = null;
        handleAudioCaptured(audioBlob);
      } catch (err) {
        console.error('Error stopping audio recorder:', err);
        setErrorMessage('Failed to capture audio from microphone.');
        setUiState('error');
      }
    }
  };


  const startStepAnimation = () => {
    setActiveStepIndex(0);
    if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
    stepIntervalRef.current = setInterval(() => {
      setActiveStepIndex(prev => (prev < 4 ? prev + 1 : prev));
    }, 450);
  };

  const stopStepAnimation = () => {
    if (stepIntervalRef.current) clearInterval(stepIntervalRef.current);
  };

  // --- Process Audio via Real Backend API ---
  const handleAudioCaptured = async (audioBlob) => {
    setUiState('uploading');
    startStepAnimation();

    try {
      setTimeout(() => {
        setUiState('waiting-for-answer');
      }, 300);

      const response = await askQuestion(audioBlob, selectedLanguage, selectedStrategy);
      stopStepAnimation();
      handlePipelineResponse(response);
    } catch (err) {
      stopStepAnimation();
      console.error('Failed to process voice query:', err);
      setErrorMessage(err.message || 'Backend service connection failed. Please verify the backend is running on port 8000.');
      setUiState('error');
    }
  };

  // --- Process Text Query via Real Backend API ---
  const handleTextSubmit = async (e, textOverride = null) => {
    if (e) e.preventDefault();
    const clean = (textOverride || textInput).trim();
    if (!clean) return;

    setUiState('waiting-for-answer');
    startStepAnimation();
    setErrorMessage('');
    setGuardrailReason('');
    setGuardrailType('');

    try {
      const response = await askTextQuestion(clean, selectedLanguage, selectedStrategy);
      stopStepAnimation();
      handlePipelineResponse(response);
      if (!textOverride) setTextInput('');
    } catch (err) {
      stopStepAnimation();
      console.error('Failed to process text query:', err);
      setErrorMessage(err.message || 'Backend connection error.');
      setUiState('error');
    }
  };

  // --- Common Response Evaluation & Guardrail Interpretation ---
  const handlePipelineResponse = (response) => {
    setResultData(response);
    const flags = response.guardrail_flags || {};

    if (flags.input_safe === false) {
      setGuardrailType('Input Safety Guardrail Refusal');
      setGuardrailReason('Query blocked: Prohibited or adversarial instruction detected by safety moderation.');
      setUiState('guardrail-refused');
      return;
    }

    if (flags.input_offtopic === true) {
      setGuardrailType('Topicality Scope Guardrail Refusal');
      setGuardrailReason('Query blocked: Conversational greeting or topic outside the MSMARCO-XI factual domain.');
      setUiState('guardrail-refused');
      return;
    }

    if (flags.retrieval_confident === false && (!response.sources || response.sources.length === 0)) {
      setGuardrailType('Low Retrieval Confidence Refusal');
      setGuardrailReason('Grounded refusal: No sufficiently relevant knowledge base passages were retrieved to support an answer.');
      setUiState('guardrail-refused');
      return;
    }

    if (flags.output_grounded === false) {
      setGuardrailType('Grounding Guardrail Refusal');
      setGuardrailReason('Grounded refusal: Proposed answer failed strict factual verification against the retrieved context.');
      setUiState('guardrail-refused');
      return;
    }

    setUiState('showing-answer');
  };

  const resetToIdle = () => {
    setUiState('idle');
    setResultData(null);
    setErrorMessage('');
    setGuardrailType('');
    setGuardrailReason('');
    setRecordingDuration(0);
    setActiveStepIndex(0);
  };

  const presets = DEMO_PRESETS[selectedLanguage] || DEMO_PRESETS.hin;

  return (
    <div className="w-full max-w-4xl mx-auto px-4 py-4 flex flex-col items-center">
      
      {/* 1. Control Row: Segmented Button Groups */}
      <SegmentedControls
        selectedLanguage={selectedLanguage}
        setSelectedLanguage={setSelectedLanguage}
        selectedStrategy={selectedStrategy}
        setSelectedStrategy={setSelectedStrategy}
      />

      {/* 2. Center Signature Element: Large Circular Instrument Mic Dial */}
      <InstrumentMicDial
        isRecording={uiState === 'recording'}
        recordingDuration={recordingDuration}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
        selectedLanguage={selectedLanguage}
      />

      {/* 3. Console / Terminal-Style Panel */}
      <div className="w-full mb-8">
        <ConsoleTelemetryPanel
          uiState={uiState}
          resultData={resultData}
          errorMessage={errorMessage}
          guardrailType={guardrailType}
          guardrailReason={guardrailReason}
          activeStepIndex={activeStepIndex}
          onReset={resetToIdle}
        />
      </div>

      {/* 4. Subordinate Text Input Fallback & 1-Click Evaluation Presets */}
      <div className="w-full max-w-2xl bg-[#10161F]/70 border border-[rgba(237,234,227,0.06)] rounded-xl p-4">
        
        {/* Quick Text Input */}
        <form onSubmit={(e) => handleTextSubmit(e)} className="flex items-center gap-2 mb-3">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder={
              selectedLanguage === 'hin' 
                ? 'या यहाँ हिंदी में टाइप करें...' 
                : selectedLanguage === 'tam' 
                ? 'அல்லது தமிழில் எழுதவும்...' 
                : 'Or type fallback query here...'
            }
            className="flex-1 px-3.5 py-2 rounded-lg bg-[#0B0F14] border border-[rgba(237,234,227,0.09)] text-xs text-[#EDEAE3] placeholder-[#606E80] focus:outline-none focus:border-[#C9A227] indic-text font-sans"
          />
          <button
            type="submit"
            disabled={!textInput.trim()}
            className="px-3 py-2 rounded-lg bg-[#C9A227] hover:bg-[#DBB434] disabled:opacity-30 text-[#0B0F14] font-mono text-xs font-bold transition-colors cursor-pointer"
            aria-label="Send text query"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* 1-Click Presets */}
        <div className="pt-2 border-t border-[rgba(237,234,227,0.05)]">
          <div className="font-mono text-[10px] text-[#606E80] uppercase tracking-wider mb-2 flex items-center gap-1">
            <Terminal className="w-3 h-3 text-[#3E8E8C]" /> 1-Click Evaluation Presets:
          </div>
          <div className="flex flex-wrap gap-1.5">
            {presets.map((item, idx) => (
              <button
                key={idx}
                onClick={() => handleTextSubmit(null, item.text)}
                className="font-mono text-[11px] px-2.5 py-1 rounded bg-[#141C27] hover:bg-[rgba(201,162,39,0.12)] border border-[rgba(237,234,227,0.06)] hover:border-[#C9A227]/40 text-[#95A1B2] hover:text-[#EDEAE3] transition-all cursor-pointer truncate max-w-full"
              >
                "{item.label}"
              </button>
            ))}
          </div>
        </div>

      </div>

    </div>
  );
}
