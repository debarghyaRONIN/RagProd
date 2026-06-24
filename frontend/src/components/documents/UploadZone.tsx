'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useChatStore } from '@/store/chatStore';
import { api } from '@/lib/api';
import { 
  UploadCloud, 
  FileText, 
  Trash2, 
  Loader2, 
  CheckCircle2, 
  AlertCircle,
  Clock
} from 'lucide-react';
import gsap from 'gsap';

export default function UploadZone() {
  const { documents, docsLoading, fetchDocuments, setDocuments, deleteDocument } = useChatStore();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const activePolls = useRef<Set<string>>(new Set());

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Set up polling for documents that are in 'pending' or 'processing' status
  useEffect(() => {
    const unfinishedDocs = documents.filter(
      (d) => d.status === 'pending' || d.status === 'processing'
    );
    
    unfinishedDocs.forEach((doc) => {
      if (!activePolls.current.has(doc.id)) {
        activePolls.current.add(doc.id);
        pollDocumentStatus(doc.id);
      }
    });
  }, [documents]);

  const pollDocumentStatus = async (docId: string) => {
    const intervalId = setInterval(async () => {
      try {
        const data = await api.get(`/documents/${docId}/status`);
        
        // Update document status in state
        setDocuments(
          useChatStore.getState().documents.map((d) => 
            d.id === docId ? { ...d, status: data.status, chunk_count: data.chunk_count, error_message: data.error_message } : d
          )
        );

        if (data.status === 'ready' || data.status === 'failed') {
          clearInterval(intervalId);
          activePolls.current.delete(docId);
        }
      } catch (err) {
        console.error(`Error polling status for doc ${docId}:`, err);
        clearInterval(intervalId);
        activePolls.current.delete(docId);
      }
    }, 2000);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    gsap.to('.drop-zone', { borderColor: '#fafafa', backgroundColor: '#18181b/40', duration: 0.2 });
  };

  const handleDragLeave = () => {
    gsap.to('.drop-zone', { borderColor: '#27272a', backgroundColor: 'transparent', duration: 0.2 });
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    handleDragLeave();
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData, // Fetch naturally sets multipart boundary for FormData
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(errData?.detail?.detail || errData?.detail || 'Upload failed');
      }

      const newDoc = await response.json();
      
      // Add to store
      setDocuments([newDoc, ...useChatStore.getState().documents]);
      
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload document');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document and its indexed vectors?')) return;
    try {
      await deleteDocument(docId);
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div ref={containerRef} className="flex flex-col gap-6 w-full max-w-4xl mx-auto p-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-medium tracking-tight">Document Workspace</h1>
        <p className="text-xs text-muted-foreground">Upload and manage files loaded into the Milvus vector index</p>
      </div>

      {/* Drag & Drop Zone */}
      <div 
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="drop-zone border border-dashed border-border rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-zinc-500 hover:bg-zinc-900/10 transition-all duration-300 min-h-[160px]"
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange} 
          className="hidden"
          accept=".pdf,.docx,.doc,.txt,.md"
        />
        
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Loader2 className="animate-spin text-muted-foreground" size={24} />
            <span className="text-xs text-muted-foreground tracking-wide font-mono">UPLOADING & CHUNKING...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-center">
            <UploadCloud className="text-muted-foreground group-hover:text-foreground transition" size={28} />
            <span className="text-sm font-medium">Drag & drop or click to upload</span>
            <span className="text-[10px] text-muted-foreground font-mono">PDF, DOCX, TXT, MD up to 50MB</span>
          </div>
        )}
      </div>

      {uploadError && (
        <div className="p-3 text-xs bg-red-950/20 border border-red-900/50 text-red-400 rounded-md flex items-center gap-2">
          <AlertCircle size={14} className="shrink-0" />
          {uploadError}
        </div>
      )}

      {/* Uploaded Documents List */}
      <div className="flex flex-col gap-3">
        <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground px-1">
          Loaded Documents ({documents.length})
        </div>

        {docsLoading && documents.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-8">Loading document library...</div>
        ) : documents.length === 0 ? (
          <div className="text-xs text-muted-foreground text-center py-8 border border-border rounded-lg bg-zinc-950/10">
            No documents indexed in this workspace. Upload files above.
          </div>
        ) : (
          <div className="flex flex-col border border-border rounded-lg divide-y divide-border overflow-hidden bg-zinc-950/10">
            {documents.map((doc) => (
              <div key={doc.id} className="p-4 flex items-center justify-between text-sm hover:bg-zinc-900/10 transition">
                <div className="flex items-center gap-3 min-w-0 pr-8">
                  <FileText className="text-muted-foreground shrink-0" size={18} />
                  <div className="flex flex-col min-w-0">
                    <span className="font-medium truncate">{doc.filename}</span>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                      <span>{formatSize(doc.file_size)}</span>
                      <span>•</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      {doc.chunk_count && (
                        <>
                          <span>•</span>
                          <span className="font-mono">{doc.chunk_count} chunks</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  {/* Status Indicator */}
                  <div className="flex items-center gap-1.5">
                    {doc.status === 'pending' && (
                      <span className="flex items-center gap-1 text-xs text-amber-500 font-mono">
                        <Clock size={12} className="animate-pulse" /> pending
                      </span>
                    )}
                    {doc.status === 'processing' && (
                      <span className="flex items-center gap-1 text-xs text-blue-500 font-mono">
                        <Loader2 size={12} className="animate-spin" /> indexing
                      </span>
                    )}
                    {doc.status === 'ready' && (
                      <span className="flex items-center gap-1 text-xs text-emerald-500 font-mono">
                        <CheckCircle2 size={12} /> ready
                      </span>
                    )}
                    {doc.status === 'failed' && (
                      <span 
                        className="flex items-center gap-1 text-xs text-red-500 font-mono cursor-help"
                        title={doc.error_message || 'Indexing failed'}
                      >
                        <AlertCircle size={12} /> failed
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-2 hover:bg-zinc-900 hover:text-destructive rounded-md text-muted-foreground transition"
                    title="Delete document"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
