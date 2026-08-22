'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api } from '@/lib/api';
import { ApiEquipoEnListado } from '@/lib/api-types';
import { Users, Search, Loader2, Trophy, ChevronRight } from 'lucide-react';

export default function EquiposPage() {
  const [equipos, setEquipos] = useState<ApiEquipoEnListado[]>([]);
  const [buscar, setBuscar] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // La búsqueda va al servidor con un respiro: sin el retraso, cada tecla
  // dispara un pedido y llegan respuestas desordenadas.
  useEffect(() => {
    let activo = true;
    setLoading(true);
    const t = setTimeout(() => {
      api.getEquipos(buscar)
        .then(data => activo && (setEquipos(data), setError(false)))
        .catch(() => activo && setError(true))
        .finally(() => activo && setLoading(false));
    }, 250);
    return () => { activo = false; clearTimeout(t); };
  }, [buscar]);

  return (
    <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100 selection:bg-violet-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-white/8 pb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white flex items-center gap-2.5">
              <Users className="text-violet-400" /> Equipos
            </h1>
            <p className="text-xs text-white/40 mt-1">
              Todos los equipos que compitieron en la plataforma, con su historial.
            </p>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
            <input
              type="text"
              value={buscar}
              onChange={e => setBuscar(e.target.value)}
              placeholder="Buscar por nombre o tag..."
              className="pl-8 pr-3 py-2.5 bg-[#11111f] border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-violet-500 w-full sm:w-64"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 text-white/40 text-sm py-20">
            <Loader2 className="animate-spin" size={18} /> Cargando equipos...
          </div>
        ) : error ? (
          <div className="bg-[#11111f] border border-rose-500/20 rounded-3xl p-10 text-center text-sm text-white/50">
            No pudimos conectar con el servidor.
          </div>
        ) : equipos.length === 0 ? (
          <div className="bg-[#11111f] border border-white/8 rounded-3xl p-12 text-center text-sm text-white/50">
            {buscar
              ? `Ningún equipo coincide con "${buscar}".`
              : 'Todavía no hay equipos aprobados en ningún torneo.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {equipos.map(e => (
              <Link
                key={e.id}
                href={`/equipos/${e.id}`}
                className="bg-[#11111f] border border-white/8 hover:border-violet-500/50 rounded-2xl p-4 flex items-center gap-3 group transition-all"
              >
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-600 flex items-center justify-center font-black text-white text-sm shrink-0">
                  {e.tag || e.nombre.slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-bold text-sm text-white truncate group-hover:text-violet-300 transition-colors">
                    {e.nombre}
                  </p>
                  <span className="text-[11px] text-white/40 flex items-center gap-2">
                    <span>{e.torneos_jugados} {e.torneos_jugados === 1 ? 'torneo' : 'torneos'}</span>
                    {e.partidas_ganadas > 0 && (
                      <span className="flex items-center gap-1 text-emerald-400/70">
                        <Trophy size={10} /> {e.partidas_ganadas}
                      </span>
                    )}
                  </span>
                </div>
                <ChevronRight size={15} className="text-white/20 group-hover:text-violet-400 transition-colors shrink-0" />
              </Link>
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
