'use client';

import React, { useEffect, useState } from 'react';
import {
  ClipboardList, CheckCircle2, XCircle, Clock, Search,
  Users, ChevronDown, ChevronUp, Check, X, Loader2, AlertCircle
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiEdicion, ApiInscripcion } from '@/lib/api-types';

interface Fila {
  inscripcion: ApiInscripcion;
  edicion: ApiEdicion;
}

export default function AdminGlobalInscripcionesPage() {
  const [ediciones, setEdiciones] = useState<ApiEdicion[]>([]);
  const [filas, setFilas] = useState<Fila[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('todos');
  const [selectedEdicion, setSelectedEdicion] = useState<string>('todas');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [procesando, setProcesando] = useState<number | null>(null);

  const cargar = async () => {
    setLoading(true);
    try {
      const eds = await api.getEdiciones();
      setEdiciones(eds);
      const listas = await Promise.all(eds.map(ed => api.getInscripciones(String(ed.id)).catch(() => [])));
      const todas: Fila[] = [];
      eds.forEach((ed, i) => listas[i].forEach(ins => todas.push({ inscripcion: ins, edicion: ed })));
      setFilas(todas);
    } catch {
      setError('No se pudieron cargar las inscripciones.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleApprove = async (fila: Fila) => {
    setProcesando(fila.inscripcion.id);
    try {
      await api.revisarInscripcion(String(fila.edicion.id), String(fila.inscripcion.id), 'aprobada');
      showToast('Inscripción aprobada.');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo aprobar.');
    } finally {
      setProcesando(null);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    const fila = filas.find(f => f.inscripcion.id === rejectingId);
    if (!fila || !rejectReason) return;
    setProcesando(fila.inscripcion.id);
    try {
      await api.revisarInscripcion(String(fila.edicion.id), String(fila.inscripcion.id), 'rechazada', rejectReason);
      setRejectingId(null);
      setRejectReason('');
      showToast('Inscripción rechazada.');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo rechazar.');
    } finally {
      setProcesando(null);
    }
  };

  const filtered = filas.filter(({ inscripcion: ins, edicion }) => {
    const matchesSearch = ins.equipo.nombre.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'todos' || ins.estado === statusFilter;
    const matchesEdicion = selectedEdicion === 'todas' || String(edicion.id) === selectedEdicion;
    return matchesSearch && matchesStatus && matchesEdicion;
  });

  const pendingCount = filas.filter(f => f.inscripcion.estado === 'pendiente').length;

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando inscripciones...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/90 text-white px-5 py-3 rounded-2xl shadow-xl backdrop-blur-md flex items-center gap-2 text-sm font-semibold">
          <CheckCircle2 size={18} /> {toastMsg}
        </div>
      )}

      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">Gestión Global</span>
          <span className="text-white/20">•</span>
          <span className="text-xs text-amber-400 font-semibold">{pendingCount} pendientes de revisión</span>
        </div>
        <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
          <ClipboardList className="text-violet-400" /> Cola de Aprobación de Inscripciones
        </h1>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle size={15} /> <span>{error}</span>
        </div>
      )}

      <div className="bg-[#13131f] border border-white/8 rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-3 text-white/30" />
          <input
            type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por equipo..."
            className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-white/30 focus:outline-none focus:border-violet-500"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={selectedEdicion} onChange={(e) => setSelectedEdicion(e.target.value)}
            className="bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500"
          >
            <option value="todas">Todas las Ediciones</option>
            {ediciones.map(ed => <option key={ed.id} value={ed.id}>{ed.nombre}</option>)}
          </select>
          <div className="flex items-center bg-[#0e0e1a] p-1 rounded-xl border border-white/10">
            {[
              { id: 'todos', label: 'Todos' },
              { id: 'pendiente', label: `Pendientes (${pendingCount})` },
              { id: 'aprobada', label: 'Aprobadas' },
              { id: 'rechazada', label: 'Rechazadas' },
            ].map(tab => (
              <button
                key={tab.id} onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${statusFilter === tab.id ? 'bg-violet-600 text-white' : 'text-white/40 hover:text-white'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="bg-[#13131f] border border-white/8 rounded-2xl p-12 text-center text-white/30">
            <Users size={36} className="mx-auto mb-2 opacity-30 text-violet-400" />
            <p className="text-sm font-semibold text-white/70">No se encontraron inscripciones con estos filtros</p>
          </div>
        ) : (
          filtered.map(({ inscripcion: ins, edicion }) => {
            const isExpanded = expandedId === ins.id;
            return (
              <div key={ins.id} className="bg-[#13131f] border border-white/8 rounded-2xl overflow-hidden hover:border-white/15 transition-all">
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-600 flex items-center justify-center font-black text-white text-xs flex-shrink-0">
                      {(ins.equipo.tag || ins.equipo.nombre.slice(0, 3)).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white leading-tight">{ins.equipo.nombre}</h3>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-white/40 mt-0.5">
                        <span className="text-cyan-400 font-semibold">{edicion.nombre}</span>
                        <span>•</span>
                        <span>{ins.jugadores.length} jugadores en plantilla</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap">
                    {ins.estado === 'pendiente' && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-500/15 border border-amber-500/30 px-2.5 py-1 rounded-full">
                        <Clock size={12} /> Pendiente
                      </span>
                    )}
                    {ins.estado === 'aprobada' && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-green-400 bg-green-500/15 border border-green-500/30 px-2.5 py-1 rounded-full">
                        <CheckCircle2 size={12} /> Aprobada
                      </span>
                    )}
                    {ins.estado === 'rechazada' && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-red-400 bg-red-500/15 border border-red-500/30 px-2.5 py-1 rounded-full">
                        <XCircle size={12} /> Rechazada
                      </span>
                    )}

                    {ins.estado === 'pendiente' && (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleApprove({ inscripcion: ins, edicion })}
                          disabled={procesando === ins.id}
                          className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-xl flex items-center gap-1 shadow-md shadow-green-600/20 disabled:opacity-50"
                        >
                          {procesando === ins.id ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Aprobar
                        </button>
                        <button
                          onClick={() => setRejectingId(ins.id)}
                          className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-300 border border-red-500/30 text-xs font-semibold rounded-xl flex items-center gap-1"
                        >
                          <X size={13} /> Rechazar
                        </button>
                      </div>
                    )}

                    <button
                      onClick={() => setExpandedId(isExpanded ? null : ins.id)}
                      className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-white/50 hover:text-white transition-colors"
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-5 bg-black/20 border-t border-white/5 space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-white/50 mb-2">
                      Plantilla de Jugadores ({ins.jugadores.length})
                    </h4>
                    {ins.jugadores.length === 0 ? (
                      <div className="p-4 rounded-xl border border-dashed border-white/10 text-center text-white/30 text-xs">
                        No se cargaron jugadores para este equipo.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {ins.jugadores.map((player) => (
                          <div
                            key={player.id}
                            className={`p-3 rounded-xl border flex items-center justify-between text-xs ${
                              player.es_capitan ? 'bg-violet-600/10 border-violet-500/30' : player.es_suplente ? 'bg-white/[0.01] border-white/5 opacity-70' : 'bg-white/[0.03] border-white/8'
                            }`}
                          >
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="font-bold text-white">{player.identidad.nick || player.identidad.nombre || `Jugador #${player.orden}`}</span>
                                {player.es_capitan && <span className="px-1.5 py-0.2 rounded bg-amber-400/20 text-amber-300 font-bold text-[9px] uppercase">Capitán</span>}
                                {player.es_suplente && <span className="px-1.5 py-0.2 rounded bg-white/10 text-white/50 text-[9px] uppercase">Suplente</span>}
                              </div>
                              <div className="text-[11px] text-white/40 font-mono mt-0.5">
                                {Object.entries(player.identidad).filter(([k]) => k !== 'nick').map(([k, v]) => `${k}: ${v}`).join(' · ')}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {rejectingId && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#13131f] border border-red-500/30 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <XCircle className="text-red-400" size={20} /> Rechazar Inscripción de Equipo
            </h3>
            <form onSubmit={handleReject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-white/60 mb-1">Motivo del Rechazo</label>
                <textarea
                  value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Ej. Faltan jugadores titulares con ID verificado..."
                  className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500 h-24 resize-none"
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button type="button" onClick={() => setRejectingId(null)} className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white/70 text-xs font-semibold rounded-xl">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-red-600/30">
                  Confirmar Rechazo
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
