'use client';

import React, { useState } from 'react';
import { RetrievedChunk } from '@/lib/types';
import { FileText, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

interface SourceCitationsProps {
  sources: RetrievedChunk[];
}

export default function SourceCitations({ sources }: SourceCitationsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeChunk, setActiveChunk] = useState<RetrievedChunk | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-zinc-900 flex flex-col gap-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider text-muted-foreground hover:text-foreground transition focus:outline-none w-fit"
      >
        <span>Sources ({sources.length})</span>
        {isOpen ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>

      {isOpen && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
          {sources.map((src, idx) => (
            <div
              key={src.id || idx}
              onClick={() => setActiveChunk(src)}
              className="p-2.5 border border-border bg-zinc-950/40 hover:bg-zinc-900/30 rounded-md cursor-pointer flex flex-col gap-1.5 min-w-0 transition hover:border-zinc-700"
            >
              <div className="flex items-center justify-between text-[11px] font-medium text-zinc-300">
                <div className="flex items-center gap-1.5 min-w-0">
                  <FileText size={11} className="shrink-0 text-muted-foreground" />
                  <span className="truncate">{src.filename}</span>
                </div>
                <span className="font-mono text-[10px] text-muted-foreground shrink-0 bg-zinc-900 px-1 py-0.5 rounded">
                  P. {src.source_page}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                {src.text}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Popover / Lightbox for viewing full source text */}
      {activeChunk && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div 
            className="w-full max-w-2xl bg-card border border-border rounded-xl flex flex-col max-h-[80vh] shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-muted-foreground" />
                <span className="text-sm font-semibold truncate max-w-[280px]">
                  {activeChunk.filename}
                </span>
                <span className="text-[10px] font-mono bg-zinc-900 border border-border px-1.5 py-0.5 rounded text-muted-foreground">
                  Page {activeChunk.source_page}
                </span>
              </div>
              <button
                onClick={() => setActiveChunk(null)}
                className="p-1 hover:bg-zinc-900 text-muted-foreground hover:text-foreground rounded transition text-xs font-mono"
              >
                CLOSE
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto text-sm text-zinc-300 leading-relaxed font-mono whitespace-pre-wrap selection:bg-zinc-800">
              {activeChunk.text}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-border bg-zinc-950/20 text-[10px] text-muted-foreground font-mono flex justify-between items-center px-4">
              <span>Similarity Relevance Score: {(activeChunk.score * 100).toFixed(1)}%</span>
              <span className="text-zinc-500">Chunk ID: {activeChunk.id}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
