'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useChatStore } from '@/store/chatStore';
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Edit3, 
  LogOut, 
  FileText, 
  Check, 
  X,
  ChevronLeft,
  ChevronRight,
  Database
} from 'lucide-react';
import { api } from '@/lib/api';
import gsap from 'gsap';

export default function Sidebar() {
  const router = useRouter();
  const params = useParams();
  
  const {
    sessions,
    currentSessionId,
    sessionsLoading,
    setCurrentSession,
    fetchSessions,
    createSession,
    renameSession,
    deleteSession
  } = useChatStore();

  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [dbStatus, setDbStatus] = useState<'ok' | 'down' | 'loading'>('loading');

  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchSessions();
    checkDatabaseHealth();
    
    // Check health every 15 seconds
    const interval = setInterval(checkDatabaseHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (params.id) {
      setCurrentSession(params.id as string);
    } else {
      setCurrentSession(null);
    }
  }, [params.id, setCurrentSession]);

  useEffect(() => {
    // Staggered session list entry transition using GSAP
    if (!sessionsLoading && sessions.length > 0) {
      gsap.fromTo('.session-item', 
        { opacity: 0, x: -10 },
        { opacity: 1, x: 0, duration: 0.4, stagger: 0.04, ease: 'power2.out' }
      );
    }
  }, [sessionsLoading, sessions.length]);

  const checkDatabaseHealth = async () => {
    try {
      const health = await api.get('/health');
      if (health.postgres === 'ok' && health.milvus === 'ok') {
        setDbStatus('ok');
      } else {
        setDbStatus('down');
      }
    } catch {
      setDbStatus('down');
    }
  };

  const handleNewChat = async () => {
    try {
      const s = await createSession();
      router.push(`/session/${s.id}`);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleRenameStart = (id: string, title: string) => {
    setRenamingId(id);
    setRenameTitle(title);
  };

  const handleRenameSave = async (id: string) => {
    if (!renameTitle.trim()) return;
    try {
      await renameSession(id, renameTitle.trim());
      setRenamingId(null);
    } catch (err) {
      console.error('Failed to rename:', err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    e.preventDefault();
    if (!confirm('Are you sure you want to delete this chat session?')) return;
    try {
      await deleteSession(id);
      if (currentSessionId === id) {
        router.push('/');
      }
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
      router.push('/login');
      router.refresh();
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  // Group sessions by date category
  const getGroupedSessions = () => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const last7Days = new Date(today);
    last7Days.setDate(last7Days.getDate() - 7);

    const groups: { [key: string]: typeof sessions } = {
      Today: [],
      Yesterday: [],
      'Last 7 Days': [],
      Older: []
    };

    sessions.forEach((s) => {
      const date = new Date(s.updated_at);
      if (date >= today) {
        groups['Today'].push(s);
      } else if (date >= yesterday) {
        groups['Yesterday'].push(s);
      } else if (date >= last7Days) {
        groups['Last 7 Days'].push(s);
      } else {
        groups['Older'].push(s);
      }
    });

    return Object.entries(groups).filter(([_, items]) => items.length > 0);
  };

  if (isCollapsed) {
    return (
      <aside className="w-14 h-screen border-r border-border bg-card flex flex-col items-center py-4 justify-between transition-all duration-300">
        <div className="flex flex-col gap-4 items-center">
          <button 
            onClick={() => setIsCollapsed(false)}
            className="p-1.5 hover:bg-zinc-900 rounded-md transition text-muted-foreground hover:text-foreground"
          >
            <ChevronRight size={16} />
          </button>
          
          <button 
            onClick={handleNewChat}
            className="p-2 bg-primary text-primary-foreground hover:bg-zinc-200 rounded-md transition"
            title="New Chat"
          >
            <Plus size={16} />
          </button>
        </div>

        <div className="flex flex-col gap-4 items-center">
          <Link href="/documents" className="p-2 hover:bg-zinc-900 rounded-md text-muted-foreground hover:text-foreground transition" title="Document Workspace">
            <FileText size={16} />
          </Link>
          <button onClick={handleLogout} className="p-2 hover:bg-zinc-900 rounded-md text-muted-foreground hover:text-destructive transition" title="Sign Out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-64 h-screen border-r border-border bg-card flex flex-col justify-between transition-all duration-300">
      {/* Header */}
      <div className="p-4 flex items-center justify-between border-b border-border">
        <div className="flex items-center gap-2">
          <span className="font-semibold tracking-tight text-sm">RAG Workspace</span>
          <div className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${
              dbStatus === 'ok' ? 'bg-emerald-500' : dbStatus === 'down' ? 'bg-red-500' : 'bg-amber-500'
            }`} />
          </div>
        </div>
        <button 
          onClick={() => setIsCollapsed(true)}
          className="p-1.5 hover:bg-zinc-900 rounded-md transition text-muted-foreground hover:text-foreground"
        >
          <ChevronLeft size={16} />
        </button>
      </div>

      {/* Main List */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-4">
        <button 
          onClick={handleNewChat}
          className="w-full py-2 px-3 border border-zinc-800 hover:border-zinc-700 bg-zinc-900/50 hover:bg-zinc-900 text-sm font-medium rounded-md transition flex items-center justify-center gap-2"
        >
          <Plus size={14} />
          New Chat
        </button>

        {sessionsLoading && sessions.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-8">Loading sessions...</div>
        ) : sessions.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-8">No chats created yet</div>
        ) : (
          <div ref={listRef} className="flex flex-col gap-4">
            {getGroupedSessions().map(([groupName, items]) => (
              <div key={groupName} className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground/80 px-2 py-1">
                  {groupName}
                </span>
                
                <div className="flex flex-col gap-0.5">
                  {items.map((session) => {
                    const isActive = currentSessionId === session.id;
                    const isEditing = renamingId === session.id;

                    return (
                      <div
                        key={session.id}
                        className={`session-item relative group w-full rounded-md text-sm transition flex items-center justify-between ${
                          isActive 
                            ? 'bg-zinc-900 text-foreground font-medium border border-zinc-800' 
                            : 'text-muted-foreground hover:text-foreground hover:bg-zinc-900/40'
                        }`}
                      >
                        {isEditing ? (
                          <div className="flex items-center gap-1 p-1 w-full">
                            <input
                              type="text"
                              value={renameTitle}
                              onChange={(e) => setRenameTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleRenameSave(session.id);
                                if (e.key === 'Escape') setRenamingId(null);
                              }}
                              autoFocus
                              className="w-full bg-zinc-950 border border-zinc-700 rounded px-1.5 py-0.5 text-xs text-foreground focus:outline-none"
                            />
                            <button 
                              onClick={() => handleRenameSave(session.id)}
                              className="p-1 hover:bg-zinc-800 text-emerald-400 rounded"
                            >
                              <Check size={12} />
                            </button>
                            <button 
                              onClick={() => setRenamingId(null)}
                              className="p-1 hover:bg-zinc-800 text-red-400 rounded"
                            >
                              <X size={12} />
                            </button>
                          </div>
                        ) : (
                          <Link
                            href={`/session/${session.id}`}
                            className="flex items-center gap-2.5 py-2 px-3.5 w-full pr-12 truncate select-none"
                          >
                            <MessageSquare size={14} className="shrink-0 opacity-70" />
                            <span className="truncate">{session.title}</span>
                          </Link>
                        )}

                        {!isEditing && (
                          <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition bg-transparent">
                            <button
                              onClick={() => handleRenameStart(session.id, session.title)}
                              className="p-1 hover:bg-zinc-800 rounded text-muted-foreground hover:text-foreground"
                              title="Rename"
                            >
                              <Edit3 size={11} />
                            </button>
                            <button
                              onClick={(e) => handleDelete(e, session.id)}
                              className="p-1 hover:bg-zinc-800 rounded text-muted-foreground hover:text-destructive"
                              title="Delete"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border flex flex-col gap-3">
        <Link 
          href="/documents"
          className="w-full py-2 px-3 border border-border bg-zinc-950/20 hover:bg-zinc-900 rounded-md text-xs text-muted-foreground hover:text-foreground font-medium flex items-center justify-center gap-2 transition"
        >
          <FileText size={13} />
          Document Library
        </Link>
        
        <button
          onClick={handleLogout}
          className="w-full py-2 px-3 border border-transparent hover:border-red-900/30 hover:bg-red-950/15 rounded-md text-xs text-muted-foreground hover:text-destructive font-medium flex items-center justify-center gap-2 transition"
        >
          <LogOut size={13} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
