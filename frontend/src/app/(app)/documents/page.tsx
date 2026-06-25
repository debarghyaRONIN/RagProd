'use client';

import React from 'react';
import UploadZone from '@/components/documents/UploadZone';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function DocumentsPage() {
  return (
    <div className="flex-1 flex flex-col h-full overflow-y-auto bg-background relative pb-12">
      {/* Header */}
      <header className="h-14 border-b border-border bg-card/50 flex items-center justify-between px-6 shrink-0 sticky top-0 z-10 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Link 
            href="/"
            className="p-1.5 hover:bg-zinc-900 rounded-md text-muted-foreground hover:text-foreground transition"
            title="Back to chat"
          >
            <ArrowLeft size={16} />
          </Link>
          <span className="font-semibold text-sm">Library Workspace</span>
        </div>
      </header>

      {/* Main Upload Zone Workspace */}
      <div className="flex-1 mt-6">
        <UploadZone />
      </div>
    </div>
  );
}
