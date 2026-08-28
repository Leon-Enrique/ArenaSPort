'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import IdentidadDeJuegoPanel from '@/components/equipos/IdentidadDeJuegoPanel';
import { api } from '@/lib/api';
import { ApiError } from '@/lib/api';
import { ApiMiEquipo, ApiMiInscripcion, ApiMiPartida } from '@/lib/api-types';
import { Usuario } from '@/types';
import {
  Shield, Users, Crown, LogIn, Loader2, Trophy, Clock, CheckCircle2, XCircle, Swords
} from 'lucide-react';

const ESTADO_PARTIDA_BADGE: Record<string, { label: (p: ApiMiPartida) => string; color: string; icon: React.ReactNode }> = {
  en_curso: { label: () => 'En curso — reportá el resultado', color: 'bg-elevada text-tinta-2 border-borde', icon: <Swords size={11} /> },
  check_in: {
    label: (p) => p.checkin_cierra_at
      ? `Check-in abierto — cierra ${new Date(p.checkin_cierra_at).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}`
      : 'Check-in abierto',
    color: 'bg-atencion/15 text-atencion border-atencion/30', icon: <LogIn size={11} />,
  },
  reportada: { label: () => 'Esperando que el rival confirme', color: 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30', icon: <Clock size={11} /> },
  programada: {
    label: (p) => p.programada_para
      ? `Programada — ${new Date(p.programada_para).toLocaleString('es', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`
      : 'Programada',
    color: 'bg-white/10 text-tinta-3 border-borde', icon: <Clock size={11} />,
  },
};

const TOKEN_KEY = 'torneos_auth_token';

const ESTADO_BADGE: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  aprobada: { label: 'Aprobada', color: 'bg-green-500/15 text-ok border-green-500/30', icon: <CheckCircle2 size={11} /> },
  pendiente: { label: 'Pendiente', color: 'bg-atencion/15 text-atencion border-atencion/30', icon: <Clock size={11} /> },
  rechazada: { label: 'Rechazada', color: 'bg-red-500/15 text-vivo border-red-500/30', icon: <XCircle size={11} /> },
};

export default function PerfilPage() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [inscripciones, setInscripciones] = useState<ApiMiInscripcion[]>([]);
  const [misPartidas, setMisPartidas] = useState<ApiMiPartida[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkedAuth, setCheckedAuth] = useState(false);

  // Equipos permanentes: la entidad que sobrevive al torneo y acumula récord.
  const [misEquipos, setMisEquipos] = useState<ApiMiEquipo[]>([]);
  const [creando, setCreando] = useState(false);
  const [nuevoNombre, setNuevoNombre] = useState('');
  const [nuevoTag, setNuevoTag] = useState('');
  const [guardandoEquipo, setGuardandoEquipo] = useState(false);
  const [errorEquipo, setErrorEquipo] = useState<string | null>(null);

  const handleCrearEquipo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nuevoNombre.trim()) return;
    setGuardandoEquipo(true);
    setErrorEquipo(null);
    try {
      const creado = await api.crearEquipo({
        nombre: nuevoNombre.trim(),
        tag: nuevoTag.trim() || undefined,
      });
      setMisEquipos(prev => [...prev, creado].sort((a, b) => a.nombre.localeCompare(b.nombre)));
      setNuevoNombre('');
      setNuevoTag('');
      setCreando(false);
    } catch (err) {
      // El caso frecuente es el 409 por nombre repetido, y el backend ya
      // manda un mensaje claro: conviene mostrarlo tal cual.
      setErrorEquipo(err instanceof ApiError ? err.message : 'No se pudo crear el equipo.');
    } finally {
      setGuardandoEquipo(false);
    }
  };

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
        return Promise.all([
          api.getMisInscripciones(),
          api.getMisPartidas(),
          api.getMisEquipos(),
        ]);
      })
      .then(([ins, partidas, equipos]) => {
        setInscripciones(ins || []);
        setMisPartidas(partidas || []);
        setMisEquipos(equipos || []);
      })
      .catch(() => {})
      .finally(() => { setCheckedAuth(true); setLoading(false); });
  }, []);

  if (loading || !checkedAuth) {
    return (
      <div className="min-h-screen flex flex-col bg-fondo text-tinta">
        <Navbar />
        <main className="flex-1 flex items-center justify-center gap-2 text-tinta-3 text-sm">
          <Loader2 className="animate-spin" size={18} /> Cargando perfil...
        </main>
        <Footer />
      </div>
    );
  }

  if (!usuario) {
    return (
      <div className="min-h-screen flex flex-col bg-fondo text-tinta">
        <Navbar />
        <main className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4 py-24">
          <Shield className="w-10 h-10 text-tinta-4" />
          <h1 className="text-xl font-bold text-white">Iniciá sesión para ver tu perfil</h1>
          <p className="text-sm text-tinta-3 max-w-sm">
            Ahí vas a ver los equipos que capitaneás y el estado de tus inscripciones en cada torneo.
          </p>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-fondo text-tinta selection:bg-acento selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-6">
        <div className="bg-superficie border border-borde rounded-[8px] p-6 sm:p-8 shadow-2xl flex items-center gap-4">
          <div className="w-14 h-14 rounded-[6px] bg-acento flex items-center justify-center font-black text-white text-xl shrink-0">
            {usuario.nombre.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h1 className="text-xl font-black text-white">{usuario.nombre}</h1>
            <span className="text-xs text-tinta-3 capitalize">{usuario.rol}</span>
          </div>
        </div>

        {/* Va primero de todo: sin el ID cargado no te pueden inscribir en
            ningún torneo, así que es lo más urgente que puede haber acá. */}
        <IdentidadDeJuegoPanel />

        <div className="space-y-3">
          <h2 className="text-sm font-bold text-tinta-2 uppercase tracking-wider flex items-center gap-2">
            <Swords size={15} className="text-tinta-2" /> Mis Partidas
          </h2>

          {misPartidas.length === 0 ? (
            <div className="glass-card p-6 text-center text-sm text-tinta-3">
              No tenés ninguna partida pendiente de check-in, en curso o esperando confirmación ahora mismo.
            </div>
          ) : (
            misPartidas.map((p) => {
              const badge = ESTADO_PARTIDA_BADGE[p.estado] ?? ESTADO_PARTIDA_BADGE['programada'];
              return (
                <Link
                  key={p.partida_id}
                  href={`/torneos/${p.edicion_slug}`}
                  className="block bg-superficie border border-borde hover:border-borde rounded-[6px] p-5 space-y-2.5 transition-all"
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-tinta-2 font-semibold">{p.torneo_nombre}</span>
                        <span className="text-tinta-4">•</span>
                        <span className="text-xs text-tinta-3">{p.fase_nombre}{p.ronda ? ` — Ronda ${p.ronda}` : ''}</span>
                      </div>
                      <h3 className="text-base font-bold text-white">
                        {p.mi_equipo_nombre || 'Tu equipo'} <span className="text-tinta-4 font-normal">vs</span> {p.rival_equipo_nombre || 'Por definir'}
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

        {/* EQUIPOS PERMANENTES — la entidad que acumula historial entre torneos */}
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h2 className="text-sm font-bold text-tinta-2 uppercase tracking-wider flex items-center gap-2">
              <Shield size={15} className="text-tinta-2" /> Equipos permanentes
            </h2>
            <button
              onClick={() => { setCreando(v => !v); setErrorEquipo(null); }}
              className="px-3.5 py-1.5 rounded-[6px] bg-elevada hover:bg-elevada border border-borde text-tinta-2 text-xs font-bold transition-all"
            >
              {creando ? 'Cancelar' : '+ Crear equipo'}
            </button>
          </div>

          <p className="text-xs text-tinta-3 leading-relaxed">
            Un equipo permanente se inscribe en varios torneos y va acumulando récord.
            Si te anotás sin elegir uno, se crea un equipo suelto que arranca de cero cada vez.
          </p>

          {creando && (
            <form onSubmit={handleCrearEquipo} className="bg-superficie border border-borde-fuerte/25 rounded-[6px] p-4 space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <input
                  type="text" required value={nuevoNombre} onChange={e => setNuevoNombre(e.target.value)}
                  placeholder="Nombre del equipo"
                  className="sm:col-span-2 bg-fondo border border-borde rounded-[6px] px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-borde-fuerte"
                />
                <input
                  type="text" value={nuevoTag} onChange={e => setNuevoTag(e.target.value)}
                  placeholder="Tag (opcional)" maxLength={12}
                  className="bg-fondo border border-borde rounded-[6px] px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-borde-fuerte"
                />
              </div>
              {errorEquipo && <p className="text-[11px] text-vivo">{errorEquipo}</p>}
              <button
                type="submit" disabled={guardandoEquipo || !nuevoNombre.trim()}
                className="px-4 py-2 rounded-[6px] bg-acento hover:bg-acento text-white text-xs font-bold disabled:opacity-50 transition-all"
              >
                {guardandoEquipo ? 'Creando...' : 'Crear equipo'}
              </button>
            </form>
          )}

          {misEquipos.length === 0 && !creando ? (
            <div className="glass-card p-6 text-center text-xs text-tinta-3">
              Todavía no tenés ningún equipo permanente.
            </div>
          ) : (
            misEquipos.map(eq => (
              <div key={eq.id} className="glass-card p-4 flex items-center gap-3">
                <div className="w-10 h-10 rounded-[6px] bg-acento flex items-center justify-center font-black text-white text-xs shrink-0">
                  {eq.tag || eq.nombre.slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-bold text-sm text-white truncate">{eq.nombre}</p>
                  <span className="text-[11px] text-tinta-3">
                    {eq.torneos_jugados} {eq.torneos_jugados === 1 ? 'torneo jugado' : 'torneos jugados'}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {/* El plantel es lo que se usa seguido; el perfil público
                      es para mirar historial. Por eso este va primero. */}
                  <Link
                    href={`/equipos/${eq.id}/roster`}
                    className="px-3 py-1.5 rounded-[4px] bg-acento/15 hover:bg-acento/25 border border-acento/30 text-acento-claro hover:text-tinta text-[11px] font-semibold transition-all flex items-center gap-1.5"
                  >
                    <Users size={11} /> Plantel
                  </Link>
                  <Link
                    href={`/equipos/${eq.id}`}
                    className="px-3 py-1.5 rounded-[4px] bg-white/5 hover:bg-white/10 border border-borde text-tinta-2 hover:text-white text-[11px] font-semibold transition-all"
                  >
                    Ver perfil
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-bold text-tinta-2 uppercase tracking-wider flex items-center gap-2">
            <Users size={15} className="text-acento-claro" /> Mis inscripciones
          </h2>

          {inscripciones.length === 0 ? (
            <div className="glass-card p-10 text-center space-y-3">
              <Trophy className="w-8 h-8 text-tinta-4 mx-auto" />
              <p className="text-sm text-tinta-3">
                Todavía no capitaneás ningún equipo. Inscribite en un torneo — si estás logueado al hacerlo, tu equipo va a aparecer acá automáticamente.
              </p>
              <Link href="/" className="inline-block px-5 py-2.5 rounded-[6px] accion-principal text-white text-xs font-bold transition-all">
                Ver torneos disponibles
              </Link>
            </div>
          ) : (
            inscripciones.map((ins) => {
              const badge = ESTADO_BADGE[ins.inscripcion.estado];
              return (
                <div key={ins.inscripcion.id} className="glass-card p-5 space-y-3">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-acento-claro font-semibold">{ins.torneo_nombre}</span>
                        <span className="text-tinta-4">•</span>
                        <span className="text-xs text-tinta-3">{ins.edicion_nombre}</span>
                      </div>
                      <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                        <Crown size={14} className="text-atencion" /> {ins.inscripcion.equipo.nombre}
                      </h3>
                    </div>
                    <span className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.color}`}>
                      {badge.icon} {badge.label}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-tinta-3">
                    <span>{ins.inscripcion.jugadores.length} jugadores</span>
                    {ins.inscripcion.seed && <span>Seed #{ins.inscripcion.seed}</span>}
                  </div>

                  <Link
                    href={`/torneos/${ins.edicion_slug}`}
                    className="inline-block px-4 py-2 bg-white/5 hover:bg-white/10 border border-borde text-tinta-2 hover:text-white text-xs font-semibold rounded-[6px] transition-all"
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
