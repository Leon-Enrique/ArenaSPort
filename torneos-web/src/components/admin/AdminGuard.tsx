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
  const [mensaje, setMensaje] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      router.replace('/');
      return;
    }
    api.setToken(token);

    const avisoLento = window.setTimeout(() => {
      if (activo) {
        setMensaje(
          'La API tarda en responder (Render free se duerme). Abre la API en otra pestaña, esperá unos segundos y refrescá esta página.',
        );
      }
    }, 20000);

    api.getMe()
      .then(u => {
        if (!activo) return;
        window.clearTimeout(avisoLento);
        if (u.rol !== 'organizador') {
          setChecking(false);
          router.replace('/');
          return;
        }
        setUsuario(u);
        setChecking(false);
      })
      .catch(() => {
        if (!activo) return;
        window.clearTimeout(avisoLento);
        localStorage.removeItem(TOKEN_KEY);
        setChecking(false);
        router.replace('/');
      });

    return () => {
      activo = false;
      window.clearTimeout(avisoLento);
    };
  }, [router]);

  if (checking || !usuario) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-fondo text-tinta-3 gap-2 text-sm px-6 text-center">
        <div className="flex items-center gap-2">
          <Loader2 className="animate-spin" size={18} /> Verificando acceso...
        </div>
        {mensaje && <p className="text-xs text-atencion/90 max-w-md">{mensaje}</p>}
      </div>
    );
  }

  return <>{children}</>;
}
