import React, { useEffect, useRef } from 'react';
import { Message } from '@/lib/types';
import ReactMarkdown from 'react-markdown';
import SourceCitations from './SourceCitations';
import { Sparkles, User } from 'lucide-react';
import gsap from 'gsap';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export default function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isAssistant = message.role === 'assistant';
  const bubbleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Only animate completed messages (avoid interrupting active stream cursor)
    if (!isStreaming && bubbleRef.current) {
      gsap.fromTo(bubbleRef.current,
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }
      );
    }
  }, [isStreaming]);

  return (
    <div 
      ref={bubbleRef}
      className={`flex gap-4 w-full max-w-4xl mx-auto py-6 border-b border-zinc-950 px-4 first-of-type:pt-4 last-of-type:border-b-0 ${
        isAssistant ? 'bg-transparent' : 'bg-zinc-950/15'
      }`}
    >
      {/* Icon / Avatar */}
      <div className={`w-8 h-8 rounded-lg border border-border flex items-center justify-center shrink-0 ${
        isAssistant ? 'bg-zinc-950 text-zinc-300' : 'bg-primary text-primary-foreground'
      }`}>
        {isAssistant ? <Sparkles size={14} /> : <User size={14} />}
      </div>

      {/* Body */}
      <div className="flex-1 flex flex-col gap-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold tracking-tight">
            {isAssistant ? 'Assistant' : 'You'}
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Message Content */}
        <div className={`text-sm leading-relaxed text-zinc-200 mt-1 select-text ${
          isStreaming ? 'cursor-blink' : ''
        }`}>
          <ReactMarkdown>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Source Citations */}
        {isAssistant && message.sources && (
          <SourceCitations sources={message.sources} />
        )}
      </div>
    </div>
  );
}
