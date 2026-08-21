import React from 'react';
import StatusBar from './components/StatusBar';
import VoiceQA from './components/VoiceQA';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col justify-between bg-[#0B0F14] text-[#EDEAE3]">
      {/* Top Status Header */}
      <StatusBar />

      {/* Main Instrument Console */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-6 w-full flex flex-col items-center">
        <VoiceQA />
      </main>

      {/* Subordinate Footer */}
      <footer className="border-t border-[rgba(237,234,227,0.06)] py-4 text-center font-mono text-[11px] text-[#606E80]">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Built with <strong>Sarvam AI (Saaras v3)</strong> • <strong>Qdrant Cloud</strong> • <strong>BAAI/bge-m3</strong>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[#3E8E8C]">● Retrieval Target &lt;200ms</span>
            <span className="text-[#C9A227]">#RAGInGoa 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
