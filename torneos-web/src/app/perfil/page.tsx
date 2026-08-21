'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api } from '@/lib/api';
import { ApiMiInscripcion, ApiMiPartida } from '@/lib/api-types';
import { Usuario } from '@/types';
import {
  Shield, Users, Crown, LogIn, Loader2, Trophy, Clock, CheckCircle2, XCircle, Swords
} from 'lucide-react';

const ESTADO_PARTIDA_BADGE: Record<string, { label: (p: ApiMiPartida) => string; color: string; icon: React.ReactNode }> = {
  en_curso: { label: () => 'En curso — reportá el resultado', color: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30', icon: <Swords size={11} /> },
  check_in: {
    label: (p) => p.checkin_cierra_at
      ? `Check-in abierto — cierra ${new Date(p.checkin_cierra_at).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}`
      : 'Check-in abierto',
    color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: <LogIn size={11} />,
  },
  reportada: { label: () => 'Esperando que el rival confirme', color: 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30', icon: <Clock size={11} /> },
  programada: {
    label: (p) => p.programada_para
      ? `Programada — ${new Date(p.programada_para).toLocaleString('es', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`
      : 'Programada',
    color: 'bg-white/10 text-white/50 border-white/10', icon: <Clock size={11} />,
  },
};

const TOKEN_KEY = 'torneos_auth_token';

const ESTADO_BADGE: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  aprobada: { label: 'Aprobada', color: 'bg-green-500/15 text-green-400 border-green-500/30', icon: <CheckCircle2 size={11} /> },
  pendiente: { label: 'Pendiente', color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: <Clock size={11} /> },
  rechazada: { label: 'Rechazada', color: 'bg-red-500/15 text-red-400 border-red-500/30', icon: <XCircle size={11} /> },
};

export default function PerfilPage() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [inscripciones, setInscripciones] = useState<ApiMiInscripcion[]>([]);
  const [misPartidas, setMisPartidas] = useState<ApiMiPartida[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkedAuth, setCheckedAuth] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setCheckedAuth(true);
      setLoading(false);
      return;
    }
    api.setToken(token);
    api.getMe()
      .then(u => {
        setUsuario(u);
        return Promise.all([api.getMisInscripciones(), api.getMisPartidas()]);
      })
      .then(([ins, partidas]) => {
        setInscripciones(ins || []);
        setMisPartidas(partidas || []);
      })
      .catch(() => {})
      .finally(() => { setCheckedAuth(true); setLoading(false); });
  }, []);

  if (loading || !checkedAuth) {
    return (
      <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100">
        <Navbar />
        <main className="flex-1 flex items-center justify-center gap-2 text-white/40 text-sm">
          <Loader2 className="animate-spin" size={18} /> Cargando perfil...
        </main>
        <Footer />
      </div>
    );
  }

  if (!usuario) {
    return (
      <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100">
        <Navbar />
        <main className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4 py-24">
          <Shield className="w-10 h-10 text-white/20" />
          <h1 className="text-xl font-bold text-white">Iniciá sesión para ver tu perfil</h1>
          <p className="text-sm text-white/50 max-w-sm">
            Ahí vas a ver los equipos que capitaneás y el estado de tus inscripciones en cada torneo.
          </p>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100 selection:bg-violet-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-6">
        <div className="bg-[#11111f] border border-white/10 rounded-3xl p-6 sm:p-8 shadow-2xl flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-violet-600 to-cyan-600 flex items-center justify-center font-black text-white text-xl shrink-0">
            {usuario.nombre.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl font-black text-white">{usuario.nombre}</h1>
            <span className="text-xs text-white/40 capitalize">{usuario.rol}</span>
          </div>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-bold text-white/60 uppercase tracking-wider flex items-center gap-2">
            <Swords size={15} className="text-cyan-400" /> Mis Partidas
          </h2>

          {misPartidas.length === 0 ? (
            <div className="bg-[#11111f] border border-white/8 rounded-2xl p-6 text-center text-sm text-white/40">
              No tenés ninguna partida pendiente de check-in, en curso o esperando confirmación ahora mismo.
            </div>
          ) : (
            misPartidas.map((p) => {
              const badge = ESTADO_PARTIDA_BADGE[p.estado] ?? ESTADO_PARTIDA_BADGE['programada'];
              return (
                <Link
                  key={p.partida_id}
                  href={`/torneos/${p.edicion_slug}`}
                  className="block bg-[#11111f] border border-white/8 hover:border-cyan-500/40 rounded-2xl p-5 space-y-2.5 transition-all"
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-cyan-400 font-semibold">{p.torneo_nombre}</span>
                        <span className="text-white/20">•</span>
                        <span className="text-xs text-white/40">{p.fase_nombre}{p.ronda ? ` — Ronda ${p.ronda}` : ''}</span>
                      </div>
                      <h3 className="text-base font-bold text-white">
                        {p.mi_equipo_nombre || 'Tu equipo'} <span className="text-white/30 font-normal">vs</span> {p.rival_equipo_nombre || 'Por definir'}
                      </h3>
                    </div>
                    <span className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border shrink-0 ${badge.color}`}>
                      {badge.icon} {badge.label(p)}
                    </span>
                  </div>
                </Link>
              );
            })
          )}
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-bold text-white/60 uppercase tracking-wider flex items-center gap-2">
            <Users size={15} className="text-violet-400" /> Mis Equipos
          </h2>

          {inscripciones.length === 0 ? (
            <div className="bg-[#11111f] border border-white/8 rounded-2xl p-10 text-center space-y-3">
              <Trophy className="w-8 h-8 text-white/20 mx-auto" />
              <p className="text-sm text-white/50">
                Todavía no capitaneás ningún equipo. Inscribite en un torneo — si estás logueado al hacerlo, tu equipo va a aparecer acá automáticamente.
              </p>
              <Link href="/" className="inline-block px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold transition-all">
                Ver torneos disponibles
              </Link>
            </div>
          ) : (
            inscripciones.map((ins) => {
              const badge = ESTADO_BADGE[ins.inscripcion.estado];
              return (
                <div key={ins.inscripcion.id} className="bg-[#11111f] border border-white/8 rounded-2xl p-5 space-y-3">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-violet-400 font-semibold">{ins.torneo_nombre}</span>
                        <span className="text-white/20">•</span>
                        <span className="text-xs text-white/40">{ins.edicion_nombre}</span>
                      </div>
                      <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                        <Crown size={14} className="text-amber-400" /> {ins.inscripcion.equipo.nombre}
                      </h3>
                    </div>
                    <span className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.color}`}>
                      {badge.icon} {badge.label}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-white/40">
                    <span>{ins.inscripcion.jugadores.length} jugadores</span>
                    {ins.inscripcion.seed && <span>Seed #{ins.inscripcion.seed}</span>}
                  </div>

                  <Link
                    href={`/torneos/${ins.edicion_slug}`}
                    className="inline-block px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white/70 hover:text-white text-xs font-semibold rounded-xl transition-all"
                  >
                    Ver Torneo
                  </Link>
                </div>
              );
            })
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
