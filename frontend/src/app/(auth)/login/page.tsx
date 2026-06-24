'use client';

import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import gsap from 'gsap';

export default function LoginPage() {
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const router = useRouter();

  useEffect(() => {
    // GSAP clean entry animation
    const ctx = gsap.context(() => {
      gsap.fromTo(containerRef.current, 
        { opacity: 0, y: 15 }, 
        { opacity: 1, y: 0, duration: 0.8, ease: 'power2.out' }
      );
      
      gsap.fromTo('.anim-item', 
        { opacity: 0, y: 10 }, 
        { opacity: 1, y: 0, duration: 0.6, stagger: 0.08, ease: 'power2.out', delay: 0.1 }
      );
    }, containerRef);
    
    return () => ctx.revert();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail || !password) return;
    
    setError(null);
    setLoading(true);
    
    try {
      await api.post('/auth/login', {
        username_or_email: usernameOrEmail,
        password: password
      });
      
      // Animate card slide-out before redirecting
      gsap.to(containerRef.current, {
        opacity: 0,
        y: -10,
        duration: 0.4,
        ease: 'power2.in',
        onComplete: () => {
          router.push('/');
          router.refresh();
        }
      });
    } catch (err: any) {
      setError(err.message || 'Login failed');
      setLoading(false);
      
      // Small shake animation on error
      gsap.fromTo(containerRef.current, 
        { x: -6 }, 
        { x: 0, duration: 0.4, ease: 'rough({template: none, strength: 2, points: 5, taper: none, randomize: true})' }
      );
    }
  };

  return (
    <main className="min-h-screen w-full flex items-center justify-center bg-background px-4">
      <div 
        ref={containerRef}
        className="w-full max-w-[380px] p-8 border border-border rounded-xl bg-card flex flex-col gap-6 opacity-0"
      >
        <div className="flex flex-col gap-1.5 text-center">
          <h1 className="text-xl font-medium tracking-tight anim-item">Sign In</h1>
          <p className="text-xs text-muted-foreground anim-item">Enter credentials to access the workspace</p>
        </div>
        
        {error && (
          <div className="p-3 text-xs bg-red-950/20 border border-red-900/50 text-red-400 rounded-md anim-item">
            {error}
          </div>
        )}
        
        <form ref={formRef} onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5 anim-item">
            <label className="text-[10px] uppercase font-semibold tracking-wider text-muted-foreground">
              Username or Email
            </label>
            <input 
              type="text" 
              value={usernameOrEmail}
              onChange={(e) => setUsernameOrEmail(e.target.value)}
              required
              disabled={loading}
              className="px-3 py-2 text-sm bg-zinc-900 border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 disabled:opacity-50 transition"
              placeholder="name@domain.com"
            />
          </div>

          <div className="flex flex-col gap-1.5 anim-item">
            <label className="text-[10px] uppercase font-semibold tracking-wider text-muted-foreground">
              Password
            </label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              className="px-3 py-2 text-sm bg-zinc-900 border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-zinc-400 disabled:opacity-50 transition"
              placeholder="••••••••"
            />
          </div>

          <button 
            type="submit"
            disabled={loading || !usernameOrEmail || !password}
            className="w-full mt-2 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-zinc-200 transition disabled:opacity-50 disabled:hover:bg-primary anim-item flex items-center justify-center gap-2"
          >
            {loading ? 'Authenticating...' : 'Continue'}
          </button>
        </form>
        
        <div className="text-xs text-center text-muted-foreground anim-item">
          Don't have an account?{' '}
          <Link href="/register" className="text-foreground hover:underline transition">
            Create account
          </Link>
        </div>
      </div>
    </main>
  );
}
