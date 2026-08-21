import React from 'react';
import { Mic, Square } from 'lucide-react';

/**
 * InstrumentMicDial Component — Center signature instrument dial button.
 * Thin animated pulse ring in brass/gold (#C9A227) while idle/active, turning coral-red (#D65A4A) during recording.
 */
export default function InstrumentMicDial({
  isRecording,
  recordingDuration,
  onStartRecording,
  onStopRecording,
  selectedLanguage,
}) {
  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col items-center justify-center my-6 sm:my-8">
      
      {/* Dial Instrument Shell */}
      <div className="relative flex items-center justify-center">
        
        {/* Animated Radial Pulse Rings */}
        {isRecording ? (
          <>
            <div className="absolute w-36 h-36 rounded-full border border-[rgba(214,90,74,0.4)] dial-pulse-ring" />
            <div className="absolute w-44 h-44 rounded-full border border-[rgba(214,90,74,0.2)] dial-pulse-ring" style={{ animationDelay: '0.6s' }} />
          </>
        ) : (
          <div className="absolute w-36 h-36 rounded-full border border-[rgba(201,162,39,0.25)] hover:border-[rgba(201,162,39,0.5)] transition-colors" />
        )}

        {/* Core Instrument Button */}
        <button
          id="mic-dial-button"
          onClick={isRecording ? onStopRecording : onStartRecording}
          className={`w-28 h-28 sm:w-32 sm:h-32 rounded-full flex flex-col items-center justify-center cursor-pointer transition-all z-10 ${
            isRecording ? 'instrument-dial-recording' : 'instrument-dial-idle'
          }`}
          aria-label={isRecording ? 'Stop voice recording' : 'Start voice recording'}
          title={isRecording ? 'Click to submit recording' : 'Click to speak question'}
        >
          {isRecording ? (
            <div className="flex flex-col items-center">
              <Square className="w-9 h-9 sm:w-10 sm:h-10 text-[#D65A4A] fill-[#D65A4A]" />
              <span className="font-mono text-[11px] font-bold text-[#D65A4A] mt-1 tracking-wider">
                {formatTimer(recordingDuration)}
              </span>
            </div>
          ) : (
            <div className="flex flex-col items-center group">
              <Mic className="w-9 h-9 sm:w-10 sm:h-10 text-[#C9A227] group-hover:scale-110 transition-transform duration-200" />
              <span className="font-mono text-[10px] text-[#95A1B2] group-hover:text-[#EDEAE3] mt-1 uppercase tracking-widest font-semibold">
                Capture
              </span>
            </div>
          )}
        </button>

      </div>

      {/* Dial Subtitle & Instruction */}
      <div className="text-center mt-4">
        <p className="font-mono text-xs text-[#95A1B2]">
          {isRecording ? (
            <span className="text-[#D65A4A] font-semibold animate-pulse">
              ● Recording voice in {selectedLanguage.toUpperCase()}... Tap to complete
            </span>
          ) : (
            <span>
              Press to record utterance in <strong className="text-[#C9A227]">{selectedLanguage === 'hin' ? 'Hindi' : selectedLanguage === 'tam' ? 'Tamil' : 'English'}</strong>
            </span>
          )}
        </p>
      </div>

    </div>
  );
}
