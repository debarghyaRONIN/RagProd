import { useRef, useCallback } from 'react';
import { useChatStore } from '../store/chatStore';
import { Message } from '../lib/types';

export function useSSE() {
  const abortControllerRef = useRef<AbortController | null>(null);
  
  const {
    setStreamingState,
    appendStreamingToken,
    setStreamingSources,
    finalizeStreaming,
    clearStreamingState
  } = useChatStore();

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setStreamingState(false);
    }
  }, [setStreamingState]);

  const send = useCallback(async (
    sessionId: string, 
    message: string, 
    docIds?: string[]
  ) => {
    // Abort previous stream if active
    abort();
    clearStreamingState();

    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    setStreamingState(true);

    try {
      const response = await fetch(`/api/sessions/${sessionId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          message,
          doc_ids: docIds || null,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorJson = await response.json().catch(() => null);
        const errMsg = errorJson?.detail?.detail || errorJson?.detail || 'Streaming connection failed';
        throw new Error(errMsg);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Readable stream not supported in response body.');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const cleanedLine = line.trim();
          if (!cleanedLine || !cleanedLine.startsWith('data: ')) {
            continue;
          }

          const rawData = cleanedLine.substring(6);
          if (!rawData) continue;

          try {
            const parsed = JSON.parse(rawData);
            
            if (parsed.type === 'token') {
              appendStreamingToken(parsed.content);
            } else if (parsed.type === 'sources') {
              setStreamingSources(parsed.sources || []);
            } else if (parsed.type === 'done') {
              // Compile the final assistant message object
              const finalMessage: Message = {
                id: parsed.message_id,
                session_id: sessionId,
                role: 'assistant',
                content: useChatStore.getState().streamingMessage,
                sources: useChatStore.getState().streamingSources,
                created_at: new Date().toISOString()
              };
              
              finalizeStreaming(sessionId, finalMessage);
            } else if (parsed.type === 'error') {
              throw new Error(parsed.detail || 'An error occurred during text generation.');
            }
          } catch (jsonErr) {
            console.warn('Failed to parse SSE JSON line payload:', rawData, jsonErr);
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('RAG stream was manually aborted by the user.');
      } else {
        console.error('SSE Stream execution error:', err);
        // Dispatch error event back to the store
        appendStreamingToken(`\n\n*[Connection Error: ${err.message}]*`);
        setStreamingState(false);
      }
    } finally {
      abortControllerRef.current = null;
    }
  }, [
    abort,
    clearStreamingState,
    setStreamingState,
    appendStreamingToken,
    setStreamingSources,
    finalizeStreaming
  ]);

  return {
    send,
    abort,
    isStreaming: useChatStore((state) => state.isStreaming),
  };
}
