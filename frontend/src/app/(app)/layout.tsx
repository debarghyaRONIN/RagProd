'use client';

import React from 'react';
import Sidebar from '@/components/sidebar/Sidebar';

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex-1 h-full relative overflow-hidden flex flex-col bg-background">
        {children}
      </div>
    </div>
  );
}
