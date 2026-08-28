'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Loader2, AlertCircle } from 'lucide-react';

const TOKEN_KEY = 'torneos_auth_token';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : '';
    const token = new URLSearchParams(hash).get('token');

    if (!token) {
      setError('No se recibió un token de Discord. Intentá iniciar sesión de nuevo.');
      return;
    }

    localStorage.setItem(TOKEN_KEY, token);
    api.setToken(token);
    api.getMe()
      .then(() => router.replace('/'))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setError('No se pudo validar la sesión con el servidor.');
      });
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-fondo text-tinta gap-3 px-4 text-center">
      {error ? (
        <>
          <AlertCircle className="w-8 h-8 text-vivo" />
          <p className="text-sm text-tinta-2 max-w-sm">{error}</p>
        </>
      ) : (
        <>
          <Loader2 className="w-8 h-8 text-acento-claro animate-spin" />
          <p className="text-sm text-tinta-3">Completando inicio de sesión...</p>
        </>
      )}
    </div>
  );
}
