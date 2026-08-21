'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Users, Crown, ChevronDown, ChevronUp,
  Check, Search, Clock, CheckCircle, XCircle, UserCheck, Loader2, AlertCircle
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiEdicion, ApiInscripcion } from '@/lib/api-types';

const ESTADO_BADGE: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  aprobada: { label: 'Aprobada', color: 'bg-green-500/15 text-green-400 border-green-500/30', icon: <CheckCircle size={11} /> },
  pendiente: { label: 'Pendiente', color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: <Clock size={11} /> },
  rechazada: { label: 'Rechazada', color: 'bg-red-500/15 text-red-400 border-red-500/30', icon: <XCircle size={11} /> },
};

export default function ParticipantesPage() {
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;

  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [inscripciones, setInscripciones] = useState<ApiInscripcion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [filtroEstado, setFiltroEstado] = useState<'todos' | 'aprobada' | 'pendiente' | 'rechazada'>('todos');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [motivoRechazo, setMotivoRechazo] = useState<Record<number, string>>({});
  const [showRechazarInput, setShowRechazarInput] = useState<number | null>(null);
  const [seedInputs, setSeedInputs] = useState<Record<number, string>>({});
  const [procesando, setProcesando] = useState<number | null>(null);

  const cargar = () => {
    setLoading(true);
    Promise.all([api.getEdicionById(edId), api.getInscripciones(edId)])
      .then(([ed, ins]) => { setEdicion(ed); setInscripciones(ins); })
      .catch(() => setError('No se pudieron cargar los participantes.'))
      .finally(() => setLoading(false));
  };

  useEffect(cargar, [edId]);

  const filtered = inscripciones.filter(ins => {
    const matchSearch = ins.equipo.nombre.toLowerCase().includes(busqueda.toLowerCase());
    const matchEstado = filtroEstado === 'todos' || ins.estado === filtroEstado;
    return matchSearch && matchEstado;
  });

  const handleAprobar = async (ins: ApiInscripcion) => {
    setProcesando(ins.id);
    setError(null);
    try {
      await api.revisarInscripcion(edId, String(ins.id), 'aprobada');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo aprobar.');
    } finally {
      setProcesando(null);
    }
  };

  const handleRechazar = async (ins: ApiInscripcion) => {
    const motivo = motivoRechazo[ins.id];
    if (!motivo?.trim()) return;
    setProcesando(ins.id);
    setError(null);
    try {
      await api.revisarInscripcion(edId, String(ins.id), 'rechazada', motivo);
      setShowRechazarInput(null);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo rechazar.');
    } finally {
      setProcesando(null);
    }
  };

  const handleGuardarSeed = async (ins: ApiInscripcion) => {
    const seed = Number(seedInputs[ins.id]);
    if (!seed) return;
    setProcesando(ins.id);
    setError(null);
    try {
      await api.editarSeedInscripcion(edId, String(ins.id), seed);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el seed.');
    } finally {
      setProcesando(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando participantes...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex items-center gap-2 text-xs text-white/30 mb-6">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">Torneo</Link>
        <span>/</span>
        <span className="text-white/60">Participantes</span>
      </div>

      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Participantes</h1>
          {edicion && <p className="text-sm text-white/40 mt-1">{edicion.nombre}</p>}
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {(['todos', 'aprobada', 'pendiente', 'rechazada'] as const).map(estado => (
            <button
              key={estado}
              onClick={() => setFiltroEstado(estado)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${filtroEstado === estado ? 'bg-violet-600 text-white' : 'bg-white/5 text-white/40 hover:text-white hover:bg-white/10'}`}
            >
              {estado === 'todos' ? 'Todos' : estado}
              {estado !== 'todos' && <span className="ml-1 opacity-60">({inscripciones.filter(i => i.estado === estado).length})</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="relative mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30" />
        <input
          type="text" placeholder="Buscar equipo..." value={busqueda} onChange={e => setBusqueda(e.target.value)}
          className="w-full bg-[#13131f] border border-white/10 text-white placeholder-white/25 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-violet-500 transition-all"
        />
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={15} /> <span>{error}</span>
        </div>
      )}

      <div className="space-y-3">
        {filtered.map((ins) => {
          const badge = ESTADO_BADGE[ins.estado];
          const isExpanded = expandedId === ins.id;

          return (
            <div key={ins.id} className={`bg-[#13131f] border rounded-2xl overflow-hidden transition-all ${
              ins.estado === 'pendiente' ? 'border-amber-500/20' : ins.estado === 'rechazada' ? 'border-red-500/10' : 'border-white/8'
            }`}>
              <div className="flex items-center gap-4 p-4 cursor-pointer hover:bg-white/3 transition-all" onClick={() => setExpandedId(isExpanded ? null : ins.id)}>
                <div className="w-8 text-center">
                  {ins.seed ? <span className="text-sm font-bold text-white/30">#{ins.seed}</span> : <span className="text-sm text-white/20">—</span>}
                </div>
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-600 flex items-center justify-center flex-shrink-0">
                    <span className="text-white font-bold text-xs">{(ins.equipo.tag || ins.equipo.nombre.slice(0, 3)).toUpperCase()}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{ins.equipo.nombre}</p>
                  </div>
                </div>
                <div className="hidden sm:flex items-center gap-1.5 text-xs text-white/40">
                  <Users size={12} /> <span>{ins.jugadores.length} jugadores</span>
                </div>
                <span className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${badge.color}`}>
                  {badge.icon} {badge.label}
                </span>
                <div className="text-white/30">{isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</div>
              </div>

              {isExpanded && (
                <div className="border-t border-white/8 p-4 space-y-4">
                  {ins.jugadores.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-white/30 uppercase text-left">
                            <th className="pb-2 font-semibold pr-4">Nick</th>
                            <th className="pb-2 font-semibold pr-4">Identidad</th>
                            <th className="pb-2 font-semibold pr-4">Discord</th>
                            <th className="pb-2 font-semibold">Rol</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {ins.jugadores.map((j) => (
                            <tr key={j.id} className="hover:bg-white/3 transition-colors">
                              <td className="py-2.5 pr-4 font-semibold text-white">
                                <div className="flex items-center gap-1.5">
                                  {j.es_capitan && <Crown size={11} className="text-amber-400 flex-shrink-0" />}
                                  {j.identidad.nick || j.identidad.nombre || `Jugador #${j.orden}`}
                                </div>
                              </td>
                              <td className="py-2.5 pr-4 text-white/60 font-mono">
                                {Object.entries(j.identidad).filter(([k]) => k !== 'nick').map(([k, v]) => `${k}: ${v}`).join(' · ')}
                              </td>
                              <td className="py-2.5 pr-4 text-white/50">{j.discord_id || '—'}</td>
                              <td className="py-2.5">
                                {j.es_capitan ? (
                                  <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 rounded-md">Capitán</span>
                                ) : j.es_suplente ? (
                                  <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded-md">Suplente</span>
                                ) : (
                                  <span className="px-1.5 py-0.5 bg-white/10 text-white/50 rounded-md">Titular</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-xs text-white/30 text-center py-4">Sin roster registrado</p>
                  )}

                  <div className="flex items-center gap-2 pt-2 border-t border-white/8 flex-wrap">
                    {ins.estado === 'pendiente' && (
                      <>
                        <button
                          onClick={() => handleAprobar(ins)}
                          disabled={procesando === ins.id}
                          className="flex items-center gap-1.5 px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 text-green-400 text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
                        >
                          {procesando === ins.id ? <Loader2 size={13} className="animate-spin" /> : <UserCheck size={13} />} Aprobar
                        </button>
                        <button
                          onClick={() => setShowRechazarInput(showRechazarInput === ins.id ? null : ins.id)}
                          className="flex items-center gap-1.5 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 text-xs font-semibold rounded-xl transition-all"
                        >
                          <XCircle size={13} /> Rechazar
                        </button>
                      </>
                    )}
                    {ins.estado === 'aprobada' && (
                      <div className="flex items-center gap-2 text-xs text-white/40">
                        <span>Seed:</span>
                        <input
                          type="number"
                          defaultValue={ins.seed ?? ''}
                          min={1}
                          onChange={e => setSeedInputs(prev => ({ ...prev, [ins.id]: e.target.value }))}
                          className="w-16 bg-white/10 border border-white/20 text-white rounded-lg px-2 py-1 text-center text-xs focus:outline-none focus:border-violet-500"
                        />
                        <button
                          onClick={() => handleGuardarSeed(ins)}
                          disabled={procesando === ins.id}
                          className="px-2 py-1 bg-violet-600/30 hover:bg-violet-600/60 text-violet-300 rounded-lg transition-all disabled:opacity-50"
                        >
                          <Check size={11} />
                        </button>
                      </div>
                    )}
                  </div>

                  {showRechazarInput === ins.id && (
                    <div className="bg-red-950/30 border border-red-500/20 rounded-xl p-4 space-y-2">
                      <label className="text-xs font-semibold text-red-400">Motivo del rechazo *</label>
                      <textarea
                        value={motivoRechazo[ins.id] ?? ''}
                        onChange={e => setMotivoRechazo(prev => ({ ...prev, [ins.id]: e.target.value }))}
                        rows={2}
                        placeholder="Ej: Roster incompleto, jugador ya inscrito en otro equipo..."
                        className="w-full bg-white/5 border border-white/10 text-white placeholder-white/25 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-red-500 transition-all resize-none"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleRechazar(ins)}
                          disabled={procesando === ins.id}
                          className="px-4 py-2 bg-red-500 hover:bg-red-400 text-white text-xs font-semibold rounded-xl transition-all disabled:opacity-50"
                        >
                          Confirmar rechazo
                        </button>
                        <button onClick={() => setShowRechazarInput(null)} className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white/60 text-xs rounded-xl transition-all">
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-16 text-white/30">
            <Users size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No hay equipos que coincidan.</p>
          </div>
        )}
      </div>
    </div>
  );
}
