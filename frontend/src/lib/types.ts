export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface Session {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface RetrievedChunk {
  id: number;
  doc_id: string;
  user_id: string;
  chunk_index: number;
  text: string;
  source_page: number;
  filename: string;
  score: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: RetrievedChunk[] | null;
  token_count?: number | null;
  created_at: string;
}

export interface Document {
  id: string;
  user_id: string;
  filename: string;
  file_size?: number;
  mime_type?: string;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  progress?: number;
  chunk_count?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface IngestionStatus {
  id: string;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  progress?: number;
  chunk_count?: number;
  error_message?: string;
}
