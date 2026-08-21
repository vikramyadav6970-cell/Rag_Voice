import React from 'react';
import { Activity, Database, Cpu } from 'lucide-react';

/**
 * StatusBar Component — Header status bar with Fraunces serif typography and live telemetry badges.
 */
export default function StatusBar() {
  return (
    <header className="border-b border-[rgba(237,234,227,0.08)] bg-[#0B0F14]/90 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        
        {/* App Title in Characterful Fraunces Serif */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[rgba(201,162,39,0.12)] border border-[rgba(201,162,39,0.3)] flex items-center justify-center text-[#C9A227] font-mono font-bold text-sm">
            RAG
          </div>
          <div>
            <h1 className="font-serif-display text-xl sm:text-2xl font-bold tracking-tight text-[#EDEAE3]">
              Indic Voice Console
            </h1>
          </div>
          <span className="hidden md:inline-flex font-mono text-[10px] text-[#95A1B2] uppercase tracking-widest px-2 py-0.5 rounded border border-[rgba(237,234,227,0.1)]">
            v0.1.0 • HH Goa 2026
          </span>
        </div>

        {/* Live Instrument Connection Badges */}
        <div className="flex items-center gap-2 sm:gap-3">
          
          {/* Qdrant Cloud Cluster Status */}
          <div className="telemetry-chip" title="Connected to AWS us-west-2 Qdrant Cloud Cluster">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="hidden sm:inline">Qdrant Cloud:</span>
            <strong className="text-[#EDEAE3] font-mono">5,536 pts</strong>
          </div>

          {/* Embedding Model */}
          <div className="telemetry-chip hidden lg:inline-flex">
            <Cpu className="w-3 h-3 text-[#3E8E8C]" />
            <span>Embed:</span>
            <strong className="text-[#EDEAE3] font-mono">bge-m3 (1024d)</strong>
          </div>

          {/* STT Engine */}
          <div className="telemetry-chip telemetry-chip-gold hidden sm:inline-flex">
            <Activity className="w-3 h-3 text-[#C9A227]" />
            <span>STT:</span>
            <strong className="font-mono">Sarvam Saaras v3</strong>
          </div>

        </div>

      </div>
    </header>
  );
}
