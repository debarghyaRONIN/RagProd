import { create } from 'zustand';
import { Session, Message, Document } from '../lib/types';
import { api } from '../lib/api';

interface ChatStore {
  // Sessions State
  sessions: Session[];
  currentSessionId: string | null;
  sessionsLoading: boolean;
  sessionsFetched: boolean;
  setCurrentSession: (id: string | null) => void;
  fetchSessions: () => Promise<void>;
  createSession: () => Promise<Session>;
  renameSession: (id: string, title: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;

  // Messages State
  messages: Record<string, Message[]>; // Keyed by session ID
  messagesLoading: boolean;
  streamingMessage: string;
  isStreaming: boolean;
  streamingSources: any[] | null;
  fetchMessages: (sessionId: string) => Promise<void>;
  addMessage: (sessionId: string, msg: Message) => void;
  setStreamingState: (isStreaming: boolean) => void;
  appendStreamingToken: (token: string) => void;
  setStreamingSources: (sources: any[] | null) => void;
  clearStreamingState: () => void;
  finalizeStreaming: (sessionId: string, msg: Message) => void;

  // Documents State
  documents: Document[];
  docsLoading: boolean;
  fetchDocuments: () => Promise<void>;
  setDocuments: (docs: Document[]) => void;
  deleteDocument: (docId: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Sessions Implementation
  sessions: [],
  currentSessionId: null,
  sessionsLoading: false,
  sessionsFetched: false,
  setCurrentSession: (id) => set({ currentSessionId: id }),
  
  fetchSessions: async () => {
    set({ sessionsLoading: true });
    try {
      const data = await api.get('/sessions');
      set({ sessions: data || [], sessionsFetched: true });
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      set({ sessionsLoading: false });
    }
  },

  createSession: async () => {
    const newSession = await api.post('/sessions');
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      currentSessionId: newSession.id,
    }));
    return newSession;
  },

  renameSession: async (id, title) => {
    const updated = await api.patch(`/sessions/${id}`, { title });
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? updated : s)),
    }));
  },

  deleteSession: async (id) => {
    await api.delete(`/sessions/${id}`);
    set((state) => {
      const filtered = state.sessions.filter((s) => s.id !== id);
      const nextSessionId = state.currentSessionId === id 
        ? (filtered.length > 0 ? filtered[0].id : null)
        : state.currentSessionId;
      
      // Clean messages key
      const newMessages = { ...state.messages };
      delete newMessages[id];

      return {
        sessions: filtered,
        currentSessionId: nextSessionId,
        messages: newMessages,
      };
    });
  },

  // Messages Implementation
  messages: {},
  messagesLoading: false,
  streamingMessage: '',
  isStreaming: false,
  streamingSources: null,

  fetchMessages: async (sessionId) => {
    set({ messagesLoading: true });
    try {
      const data = await api.get(`/sessions/${sessionId}/messages`);
      set((state) => ({
        messages: {
          ...state.messages,
          [sessionId]: data || [],
        },
      }));
    } catch (err) {
      console.error(`Failed to fetch messages for session ${sessionId}:`, err);
    } finally {
      set({ messagesLoading: false });
    }
  },

  addMessage: (sessionId, msg) => {
    set((state) => {
      const list = state.messages[sessionId] || [];
      return {
        messages: {
          ...state.messages,
          [sessionId]: [...list, msg],
        },
      };
    });
  },

  setStreamingState: (isStreaming) => set({ isStreaming }),
  
  appendStreamingToken: (token) => 
    set((state) => ({ streamingMessage: state.streamingMessage + token })),

  setStreamingSources: (sources) => set({ streamingSources: sources }),

  clearStreamingState: () => 
    set({ streamingMessage: '', streamingSources: null, isStreaming: false }),

  finalizeStreaming: (sessionId, msg) => {
    set((state) => {
      const list = state.messages[sessionId] || [];
      // Clean streaming state and append finalized message to the thread
      return {
        isStreaming: false,
        streamingMessage: '',
        streamingSources: null,
        messages: {
          ...state.messages,
          [sessionId]: [...list, msg],
        },
      };
    });
    // Refresh sessions list because the title or updated_at date changed
    get().fetchSessions();
  },

  // Documents Implementation
  documents: [],
  docsLoading: false,
  
  fetchDocuments: async () => {
    set({ docsLoading: true });
    try {
      const data = await api.get('/documents');
      set({ documents: data || [] });
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      set({ docsLoading: false });
    }
  },

  setDocuments: (docs) => set({ documents: docs }),

  deleteDocument: async (docId) => {
    await api.delete(`/documents/${docId}`);
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== docId),
    }));
  },
}));
