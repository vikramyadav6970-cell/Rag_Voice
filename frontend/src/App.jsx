import React, { useState } from 'react';
import VoiceQA from './components/VoiceQA';
import { Sparkles, Globe, Layers, Activity, ShieldCheck, Github } from 'lucide-react';

export default function App() {
  const [selectedLanguage, setSelectedLanguage] = useState('hin');
  const [selectedStrategy, setSelectedStrategy] = useState('passage_native');

  const languages = [
    { code: 'hin', label: 'हिंदी (Hindi)', script: 'नमस्ते, प्रश्न पूछें' },
    { code: 'tam', label: 'தமிழ் (Tamil)', script: 'வணக்கம், கேளுங்கள்' },
    { code: 'en', label: 'English', script: 'Ask any question' },
  ];

  const strategies = [
    { code: 'passage_native', label: 'Passage Native', desc: 'Full MSMARCO paragraph baseline' },
    { code: 'fixed_size', label: 'Fixed Size (128t)', desc: 'Word-boundary sliding window + 32t overlap' },
    { code: 'semantic', label: 'Semantic (Sentence-cut)', desc: 'Dynamic cosine-similarity cut boundaries' },
    { code: 'hierarchical_child', label: 'Hierarchical', desc: 'Child chunk vector search + Parent resolution' },
  ];

  return (
    <div className="min-h-screen flex flex-col justify-between text-gray-100">
      {/* Top Navigation Bar */}
      <header className="border-b border-gray-800/80 bg-gray-950/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-lg sm:text-xl tracking-tight bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent">
                Indic Voice RAG
              </span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 font-semibold hidden sm:inline-block">
                HH Goa 2026
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium">
              <Activity className="w-3.5 h-3.5" /> Qdrant Cloud (5,536 pts)
            </span>
          </div>
        </div>
      </header>

      {/* Hero & Controls Section */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 py-6 w-full flex flex-col items-center">
        {/* Controls Grid */}
        <div className="w-full max-w-4xl mb-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
          
          {/* Language Selector */}
          <div className="glass-panel p-4">
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-indigo-400" /> Target Language
            </label>
            <div className="grid grid-cols-3 gap-2">
              {languages.map(lang => (
                <button
                  key={lang.code}
                  onClick={() => setSelectedLanguage(lang.code)}
                  className={`px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer text-center ${
                    selectedLanguage === lang.code
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 border border-indigo-400'
                      : 'bg-gray-800/60 hover:bg-gray-800 text-gray-300 border border-gray-700/50'
                  }`}
                >
                  <div>{lang.label.split(' ')[0]}</div>
                  <div className="text-[10px] text-gray-400 font-normal">{lang.code.toUpperCase()}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Chunking Strategy Selector */}
          <div className="glass-panel p-4">
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-indigo-400" /> Chunking Strategy
            </label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-xs font-medium bg-gray-800/80 border border-gray-700 text-gray-200 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {strategies.map(s => (
                <option key={s.code} value={s.code}>
                  {s.label} — {s.desc}
                </option>
              ))}
            </select>
            <div className="mt-1.5 text-[11px] text-gray-400 truncate">
              {strategies.find(s => s.code === selectedStrategy)?.desc}
            </div>
          </div>

        </div>

        {/* Core Voice QA Interface */}
        <VoiceQA 
          selectedLanguage={selectedLanguage}
          selectedStrategy={selectedStrategy}
        />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800/80 py-6 text-center text-xs text-gray-500">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Built with <strong>Sarvam AI Saaras v3</strong>, <strong>Qdrant Cloud</strong>, <strong>bge-m3</strong>, and <strong>FastAPI</strong>.
          </div>
          <div className="flex items-center gap-4 text-gray-400">
            <span>#RAGInGoa 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
