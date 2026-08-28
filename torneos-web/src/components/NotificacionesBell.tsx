'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, CheckCheck, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { ApiNotificacion } from '@/lib/api-types';

const INTERVALO_REFRESCO_MS = 60_000;

function haceCuanto(iso: string): string {
  const minutos = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutos < 1) return 'recién';
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  return `hace ${Math.floor(horas / 24)} d`;
}

export default function NotificacionesBell() {
  const router = useRouter();
  const [items, setItems] = useState<ApiNotificacion[]>([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(true);
  const contenedor = useRef<HTMLDivElement>(null);

  const refrescar = useCallback(() => {
    return api.getNotificaciones()
      .then(b => { setItems(b.items); setNoLeidas(b.no_leidas); })
      .catch(() => { /* silencio: la campanita no puede romper la barra */ })
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    refrescar();
    const id = setInterval(refrescar, INTERVALO_REFRESCO_MS);
    return () => clearInterval(id);
  }, [refrescar]);

  // Cerrar al hacer click afuera — sin esto el panel queda abierto tapando
  // la navegación cuando el usuario se va a otra parte de la página.
  useEffect(() => {
    if (!abierto) return;
    const alClickear = (e: MouseEvent) => {
      if (contenedor.current && !contenedor.current.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener('mousedown', alClickear);
    return () => document.removeEventListener('mousedown', alClickear);
  }, [abierto]);

  const abrirNotificacion = async (n: ApiNotificacion) => {
    setAbierto(false);
    if (!n.leida_at) {
      setItems(prev => prev.map(i => (i.id === n.id ? { ...i, leida_at: new Date().toISOString() } : i)));
      setNoLeidas(c => Math.max(0, c - 1));
      api.marcarNotificacionLeida(n.id).catch(refrescar);
    }
    if (n.url) router.push(n.url);
  };

  const marcarTodas = async () => {
    setNoLeidas(0);
    setItems(prev => prev.map(i => (i.leida_at ? i : { ...i, leida_at: new Date().toISOString() })));
    api.marcarTodasLeidas().catch(refrescar);
  };

  return (
    <div className="relative" ref={contenedor}>
      <button
        onClick={() => setAbierto(!abierto)}
        aria-label={noLeidas > 0 ? `Notificaciones (${noLeidas} sin leer)` : 'Notificaciones'}
        className="relative flex items-center justify-center w-10 h-10 rounded-full bg-superficie border border-borde hover:border-acento transition-all"
      >
        <Bell className="w-4 h-4 text-tinta-2" />
        {noLeidas > 0 && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-black flex items-center justify-center border-2 border-slate-950">
            {noLeidas > 9 ? '9+' : noLeidas}
          </span>
        )}
      </button>

      {abierto && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[26rem] overflow-y-auto glass-card rounded-[6px] shadow-2xl border border-borde z-50 bg-fondo">
          <div className="flex items-center justify-between px-4 py-3 border-b border-borde sticky top-0 bg-fondo">
            <span className="text-xs font-bold text-white">
              Notificaciones{noLeidas > 0 ? ` (${noLeidas})` : ''}
            </span>
            {noLeidas > 0 && (
              <button
                onClick={marcarTodas}
                className="text-[11px] text-tinta-2 hover:text-tinta-2 font-semibold flex items-center gap-1"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Marcar todas
              </button>
            )}
          </div>

          {cargando ? (
            <div className="flex items-center justify-center gap-2 text-tinta-3 text-xs py-10">
              <Loader2 className="animate-spin" size={14} /> Cargando...
            </div>
          ) : items.length === 0 ? (
            <p className="text-xs text-tinta-3 text-center py-10 px-6">
              No tenés notificaciones todavía. Acá te van a llegar los avisos de tus torneos.
            </p>
          ) : (
            <ul className="divide-y divide-slate-800/60">
              {items.map(n => (
                <li key={n.id}>
                  <button
                    onClick={() => abrirNotificacion(n)}
                    className={`w-full text-left px-4 py-3 hover:bg-elevada/50 transition-colors flex gap-3 ${
                      n.leida_at ? '' : 'bg-elevada/20'
                    }`}
                  >
                    <span
                      className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                        n.leida_at ? 'bg-transparent' : 'bg-purple-400'
                      }`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className={`block text-xs leading-snug ${n.leida_at ? 'text-tinta-2' : 'text-white font-bold'}`}>
                        {n.titulo}
                      </span>
                      <span className="block text-[11px] text-tinta-3 mt-0.5 whitespace-pre-line line-clamp-2">
                        {n.cuerpo}
                      </span>
                      <span className="block text-[10px] text-tinta-4 mt-1 font-mono">
                        {haceCuanto(n.created_at)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
