'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Usuario } from '@/types';

const TOKEN_KEY = 'torneos_auth_token';

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      router.replace('/');
      return;
    }
    api.setToken(token);
    api.getMe()
      .then(u => {
        if (u.rol !== 'organizador') {
          router.replace('/');
          return;
        }
        setUsuario(u);
        setChecking(false);
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        router.replace('/');
      });
  }, [router]);

  if (checking || !usuario) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#08080f] text-white/40 gap-2 text-sm">
        <Loader2 className="animate-spin" size={18} /> Verificando acceso...
      </div>
    );
  }

  return <>{children}</>;
}
