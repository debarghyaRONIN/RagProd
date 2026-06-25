'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useChatStore } from '@/store/chatStore';
import { useSSE } from '@/hooks/useSSE';
import ChatWindow from '@/components/chat/ChatWindow';
import { 
  ArrowUp, 
  Paperclip, 
  FileText, 
  Check, 
  Sparkles,
  StopCircle,
  FolderOpen
} from 'lucide-react';
import Link from 'next/link';

export default function ChatSessionPage() {
  const { id } = useParams();
  const sessionId = id as string;
  const router = useRouter();

  const {
    messages,
    fetchMessages,
    currentSessionId,
    sessions,
    sessionsFetched,
    documents,
    fetchDocuments
  } = useChatStore();

  const { send, abort, isStreaming } = useSSE();

  // Redirect to home if session doesn't exist in loaded sessions list
  useEffect(() => {
    if (sessionsFetched) {
      const exists = sessions.some((s) => s.id === sessionId);
      if (!exists) {
        router.push('/');
      }
    }
  }, [sessions, sessionsFetched, sessionId, router]);

  const [input, setInput] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [showDocSelector, setShowDocSelector] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch history for this session
  useEffect(() => {
    if (sessionId) {
      fetchMessages(sessionId);
    }
    fetchDocuments();
  }, [sessionId, fetchMessages, fetchDocuments]);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDocSelector(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    
    const query = input.trim();
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // Optimistically add user message to list
    const tempUserMsg = {
      id: Math.random().toString(),
      session_id: sessionId,
      role: 'user' as const,
      content: query,
      created_at: new Date().toISOString()
    };
    useChatStore.getState().addMessage(sessionId, tempUserMsg);

    // Call streaming endpoint
    await send(sessionId, query, selectedDocIds.length > 0 ? selectedDocIds : undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea heights based on input length
  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [input]);

  const activeSession = sessions.find((s) => s.id === sessionId);
  const sessionMessages = messages[sessionId] || [];

  const toggleDocSelection = (docId: string) => {
    setSelectedDocIds((prev) => 
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background relative">
      {/* Header */}
      <header className="h-14 border-b border-border bg-card/50 flex items-center justify-between px-6 z-10 shrink-0">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-sm truncate max-w-[280px]">
            {activeSession?.title || 'Chat Workspace'}
          </span>
          {selectedDocIds.length > 0 && (
            <span className="text-[10px] font-mono bg-zinc-900 border border-border text-muted-foreground px-2 py-0.5 rounded-full">
              Scoped to {selectedDocIds.length} file{selectedDocIds.length > 1 ? 's' : ''}
            </span>
          )}
        </div>

        <Link 
          href="/documents"
          className="text-xs text-muted-foreground hover:text-foreground hover:underline transition flex items-center gap-1.5 font-medium"
        >
          <FolderOpen size={12} />
          Files
        </Link>
      </header>

      {/* Message List */}
      <ChatWindow messages={sessionMessages} />

      {/* Floating Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background via-background/95 to-transparent z-10 pointer-events-none">
        <div className="max-w-2xl mx-auto w-full flex flex-col gap-2 relative pointer-events-auto">
          
          {/* Document Scope Selector Dropdown */}
          {showDocSelector && (
            <div 
              ref={dropdownRef}
              className="absolute bottom-full mb-2 w-72 left-0 bg-card border border-border rounded-xl shadow-2xl p-3 flex flex-col gap-2 max-h-64 z-20"
            >
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground px-1 py-0.5">
                Scope Query To Documents
              </span>
              
              <div className="overflow-y-auto flex flex-col gap-0.5 max-h-48 pr-1">
                {documents.filter(d => d.status === 'ready').length === 0 ? (
                  <div className="text-xs text-muted-foreground text-center py-4">
                    No processed documents found.{' '}
                    <Link href="/documents" className="text-foreground underline">
                      Upload files
                    </Link>
                  </div>
                ) : (
                  documents.filter(d => d.status === 'ready').map((doc) => {
                    const isSelected = selectedDocIds.includes(doc.id);
                    return (
                      <div
                        key={doc.id}
                        onClick={() => toggleDocSelection(doc.id)}
                        className={`p-2 rounded-lg text-xs flex items-center justify-between cursor-pointer transition ${
                          isSelected 
                            ? 'bg-zinc-900 text-foreground font-medium border border-zinc-800' 
                            : 'text-muted-foreground hover:text-foreground hover:bg-zinc-900/40 border border-transparent'
                        }`}
                      >
                        <div className="flex items-center gap-2 min-w-0 pr-4">
                          <FileText size={12} className="shrink-0 text-muted-foreground" />
                          <span className="truncate">{doc.filename}</span>
                        </div>
                        {isSelected && <Check size={12} className="shrink-0 text-zinc-200" />}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* Prompt Box */}
          <div className="relative border border-border bg-zinc-900/40 focus-within:border-zinc-700 focus-within:bg-zinc-900/60 rounded-xl transition-all duration-300 overflow-hidden pr-12 pl-3">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents..."
              disabled={isStreaming}
              className="w-full bg-transparent resize-none text-sm text-zinc-100 placeholder-muted-foreground py-3.5 focus:outline-none max-h-[180px] pr-2"
            />
            
            {/* Attachment paperclip */}
            <button
              onClick={() => setShowDocSelector(!showDocSelector)}
              className={`absolute left-3.5 bottom-3.5 p-1.5 rounded-lg hover:bg-zinc-800 transition ${
                selectedDocIds.length > 0 || showDocSelector ? 'text-foreground bg-zinc-800/50' : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Scope query to documents"
            >
              <Paperclip size={14} />
            </button>

            {/* Action buttons (send / stop) */}
            <div className="absolute right-3.5 bottom-3.5 flex items-center gap-1.5">
              {isStreaming ? (
                <button
                  onClick={abort}
                  className="p-1.5 bg-red-950/40 hover:bg-red-900/40 text-red-400 rounded-lg transition border border-red-900/30"
                  title="Stop generation"
                >
                  <StopCircle size={14} />
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
                  className="p-1.5 bg-primary text-primary-foreground hover:bg-zinc-200 rounded-lg transition disabled:opacity-30 disabled:hover:bg-primary"
                  title="Send message"
                >
                  <ArrowUp size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
