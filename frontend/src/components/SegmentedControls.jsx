import React from 'react';
import { Globe, Layers } from 'lucide-react';

/**
 * SegmentedControls Component — Real segmented pill button groups for language and chunking strategy.
 */
export default function SegmentedControls({
  selectedLanguage,
  setSelectedLanguage,
  selectedStrategy,
  setSelectedStrategy,
}) {
  const languages = [
    { code: 'hin', label: 'हिंदी (Hindi)', script: 'देवनागरी' },
    { code: 'tam', label: 'தமிழ் (Tamil)', script: 'தமிழ்' },
    { code: 'en', label: 'English', script: 'Latin' },
  ];

  const strategies = [
    { code: 'passage_native', label: 'Passage Native', tag: 'Native' },
    { code: 'fixed_size', label: 'Fixed (128t)', tag: 'Fixed' },
    { code: 'semantic', label: 'Semantic (Cut)', tag: 'Semantic' },
    { code: 'hierarchical_child', label: 'Hierarchical', tag: 'Parent-Child' },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
      
      {/* Language Segmented Control */}
      <div className="bg-[#10161F] border border-[rgba(237,234,227,0.08)] rounded-xl p-2.5">
        <div className="flex items-center justify-between mb-2 px-1">
          <span className="font-mono text-[11px] font-semibold text-[#95A1B2] uppercase tracking-wider flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-[#C9A227]" /> Target Language
          </span>
          <span className="font-mono text-[10px] text-[#606E80]">
            AI4Bharat MSMARCO-XI
          </span>
        </div>
        <div className="grid grid-cols-3 gap-1 bg-[#0B0F14]/70 p-1 rounded-lg border border-[rgba(237,234,227,0.05)]">
          {languages.map((lang) => {
            const isActive = selectedLanguage === lang.code;
            return (
              <button
                key={lang.code}
                onClick={() => setSelectedLanguage(lang.code)}
                className={`segmented-btn ${isActive ? 'segmented-btn-active' : 'segmented-btn-inactive'}`}
                aria-pressed={isActive}
              >
                <div className="truncate">{lang.label.split(' ')[0]}</div>
                <div className="text-[9px] opacity-70 font-normal">{lang.script}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Chunking Strategy Segmented Control */}
      <div className="bg-[#10161F] border border-[rgba(237,234,227,0.08)] rounded-xl p-2.5">
        <div className="flex items-center justify-between mb-2 px-1">
          <span className="font-mono text-[11px] font-semibold text-[#95A1B2] uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-[#3E8E8C]" /> Chunking Strategy
          </span>
          <span className="font-mono text-[10px] text-[#3E8E8C]">
            Dynamic Retrieval Filter
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 bg-[#0B0F14]/70 p-1 rounded-lg border border-[rgba(237,234,227,0.05)]">
          {strategies.map((strat) => {
            const isActive = selectedStrategy === strat.code;
            return (
              <button
                key={strat.code}
                onClick={() => setSelectedStrategy(strat.code)}
                className={`segmented-btn ${isActive ? 'segmented-btn-active' : 'segmented-btn-inactive'}`}
                aria-pressed={isActive}
              >
                <div className="truncate">{strat.tag}</div>
                <div className="text-[9px] opacity-70 font-normal truncate">
                  {strat.code === 'passage_native' ? 'Baseline' : strat.code === 'fixed_size' ? '128 tok' : strat.code === 'semantic' ? 'Cosine' : 'Hierarch.'}
                </div>
              </button>
            );
          })}
        </div>
      </div>

    </div>
  );
}
