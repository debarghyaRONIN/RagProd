'use client';

import React, { useEffect, useRef } from 'react';
import { Message } from '@/lib/types';
import MessageBubble from './MessageBubble';
import { useChatStore } from '@/store/chatStore';

interface ChatWindowProps {
  messages: Message[];
}

export default function ChatWindow({ messages }: ChatWindowProps) {
  const { isStreaming, streamingMessage, streamingSources, streamingError, messagesLoading } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Scroll to bottom on initial load, new messages, streaming tokens, or errors
  useEffect(() => {
    scrollToBottom();
  }, [messages.length, streamingMessage, isStreaming, streamingError]);

  if (messagesLoading && messages.length === 0) {
    return (
      <div className="flex-1 w-full flex flex-col items-center justify-center gap-3">
        <div className="w-5 h-5 rounded-full border border-border border-t-zinc-400 animate-spin" />
        <span className="text-[10px] text-muted-foreground tracking-wider font-mono">LOADING CHAT HISTORY...</span>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full overflow-y-auto flex flex-col">
      <div className="flex-1 flex flex-col min-h-full">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted-foreground max-w-md mx-auto gap-2">
            <span className="text-sm font-medium text-zinc-300">Start the conversation</span>
            <span className="text-xs">
              Ask a question about your indexed documents. Citations and sources will appear below assistant answers.
            </span>
          </div>
        ) : (
          <div className="flex flex-col w-full">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}

            {/* Render Streaming Message */}
            {isStreaming && (streamingMessage || streamingSources) && (
              <MessageBubble 
                message={{
                  id: 'streaming-temp-id',
                  session_id: 'active-session-id',
                  role: 'assistant',
                  content: streamingMessage,
                  sources: streamingSources || null,
                  created_at: new Date().toISOString()
                }}
                isStreaming={true}
              />
            )}

            {streamingError && (
              <div className="mx-6 my-4 p-4 border border-red-900/50 bg-red-950/20 text-red-400 rounded-md text-xs font-mono flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                <span>Error: {streamingError}</span>
              </div>
            )}
          </div>
        )}
        <div ref={messagesEndRef} className="h-28 shrink-0" />
      </div>
    </div>
  );
}
