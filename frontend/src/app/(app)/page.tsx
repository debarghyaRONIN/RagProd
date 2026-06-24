'use client';

import React, { useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useChatStore } from '@/store/chatStore';
import { Plus, ArrowRight, Sparkles } from 'lucide-react';
import gsap from 'gsap';

export default function AppLandingPage() {
  const router = useRouter();
  const { sessions, sessionsLoading, createSession, fetchSessions } = useChatStore();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initial fetch to load sessions
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    // Redirect to the latest session if available
    if (!sessionsLoading && sessions.length > 0) {
      router.push(`/session/${sessions[0].id}`);
    }
  }, [sessions, sessionsLoading, router]);

  useEffect(() => {
    // Animations for welcome state
    if (!sessionsLoading && sessions.length === 0) {
      const ctx = gsap.context(() => {
        gsap.fromTo(containerRef.current,
          { opacity: 0, y: 15 },
          { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }
        );
        
        gsap.fromTo('.welcome-item',
          { opacity: 0, y: 10 },
          { opacity: 1, y: 0, duration: 0.6, stagger: 0.08, ease: 'power2.out', delay: 0.1 }
        );
      }, containerRef);
      return () => ctx.revert();
    }
  }, [sessionsLoading, sessions.length]);

  const handleStartSession = async () => {
    try {
      const s = await createSession();
      router.push(`/session/${s.id}`);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  if (sessionsLoading || sessions.length > 0) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-5 h-5 rounded-full border border-border border-t-zinc-400 animate-spin" />
          <span className="text-xs text-muted-foreground tracking-wider font-mono">INITIALIZING WORKSPACE...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex items-center justify-center bg-background px-6">
      <div 
        ref={containerRef}
        className="max-w-[420px] flex flex-col gap-6 text-center opacity-0"
      >
        <div className="flex justify-center welcome-item">
          <div className="p-3 border border-border rounded-xl bg-zinc-900/50 text-zinc-300">
            <Sparkles size={24} />
          </div>
        </div>

        <div className="flex flex-col gap-2 welcome-item">
          <h1 className="text-2xl font-medium tracking-tight">RAG QA Engine</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Upload PDFs, documents, or texts to index them into Milvus standalone vector database, and stream precise answers back.
          </p>
        </div>

        <div className="welcome-item">
          <button 
            onClick={handleStartSession}
            className="w-full py-3 px-4 bg-primary text-primary-foreground hover:bg-zinc-200 text-sm font-medium rounded-md transition flex items-center justify-center gap-2 group"
          >
            Create New Chat
            <ArrowRight size={14} className="group-hover:translate-x-0.5 transition" />
          </button>
        </div>
      </div>
    </div>
  );
}
