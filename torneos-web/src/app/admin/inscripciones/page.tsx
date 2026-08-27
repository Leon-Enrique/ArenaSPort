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
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando inscripciones...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/90 text-white px-5 py-3 rounded-[6px] shadow-xl backdrop-blur-md flex items-center gap-2 text-sm font-semibold">
          <CheckCircle2 size={18} /> {toastMsg}
        </div>
      )}

      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-acento-claro uppercase tracking-wider">Gestión Global</span>
          <span className="text-tinta-4">•</span>
          <span className="text-xs text-atencion font-semibold">{pendingCount} pendientes de revisión</span>
        </div>
        <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
          <ClipboardList className="text-acento-claro" /> Cola de Aprobación de Inscripciones
        </h1>
      </div>

      {error && (
        <div className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
          <AlertCircle size={15} /> <span>{error}</span>
        </div>
      )}

      <div className="bg-superficie border border-borde rounded-[6px] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-3 text-tinta-4" />
          <input
            type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por equipo..."
            className="w-full bg-fondo border border-borde rounded-[6px] pl-9 pr-4 py-2 text-xs text-white placeholder-white/30 focus:outline-none focus:border-acento"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={selectedEdicion} onChange={(e) => setSelectedEdicion(e.target.value)}
            className="bg-fondo border border-borde rounded-[6px] px-3 py-2 text-xs text-white focus:outline-none focus:border-acento"
          >
            <option value="todas">Todas las Ediciones</option>
            {ediciones.map(ed => <option key={ed.id} value={ed.id}>{ed.nombre}</option>)}
          </select>
          <div className="flex items-center bg-fondo p-1 rounded-[6px] border border-borde">
            {[
              { id: 'todos', label: 'Todos' },
              { id: 'pendiente', label: `Pendientes (${pendingCount})` },
              { id: 'aprobada', label: 'Aprobadas' },
              { id: 'rechazada', label: 'Rechazadas' },
            ].map(tab => (
              <button
                key={tab.id} onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1 rounded-[4px] text-xs font-semibold transition-all ${statusFilter === tab.id ? 'bg-acento text-white' : 'text-tinta-3 hover:text-white'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="bg-superficie border border-borde rounded-[6px] p-12 text-center text-tinta-4">
            <Users size={36} className="mx-auto mb-2 opacity-30 text-acento-claro" />
            <p className="text-sm font-semibold text-tinta-2">No se encontraron inscripciones con estos filtros</p>
          </div>
        ) : (
          filtered.map(({ inscripcion: ins, edicion }) => {
            const isExpanded = expandedId === ins.id;
            return (
              <div key={ins.id} className="bg-superficie border border-borde rounded-[6px] overflow-hidden hover:border-borde-fuerte transition-all">
                <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-10 h-10 rounded-[6px] bg-acento flex items-center justify-center font-black text-white text-xs flex-shrink-0">
                      {(ins.equipo.tag || ins.equipo.nombre.slice(0, 3)).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white leading-tight">{ins.equipo.nombre}</h3>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-tinta-3 mt-0.5">
                        <span className="text-tinta-2 font-semibold">{edicion.nombre}</span>
                        <span>•</span>
                        <span>{ins.jugadores.length} jugadores en plantilla</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-wrap">
                    {ins.estado === 'pendiente' && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-atencion bg-amber-500/15 border border-amber-500/30 px-2.5 py-1 rounded-full">
                        <Clock size={12} /> Pendiente
                      </span>
                    )}
                    {ins.estado === 'aprobada' && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-ok bg-green-500/15 border border-green-500/30 px-2.5 py-1 rounded-full">
                        <CheckCircle2 size={12} /> Aprobada
                      </span>
                    )}
                    {ins.estado === 'rechazada' && (
                      <span className="inline-flex items-center gap-1 text-xs font-bold text-vivo bg-red-500/15 border border-red-500/30 px-2.5 py-1 rounded-full">
                        <XCircle size={12} /> Rechazada
                      </span>
                    )}

                    {ins.estado === 'pendiente' && (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleApprove({ inscripcion: ins, edicion })}
                          disabled={procesando === ins.id}
                          className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white text-xs font-bold rounded-[6px] flex items-center gap-1 shadow-md shadow-green-600/20 disabled:opacity-50"
                        >
                          {procesando === ins.id ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Aprobar
                        </button>
                        <button
                          onClick={() => setRejectingId(ins.id)}
                          className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-vivo border border-red-500/30 text-xs font-semibold rounded-[6px] flex items-center gap-1"
                        >
                          <X size={13} /> Rechazar
                        </button>
                      </div>
                    )}

                    <button
                      onClick={() => setExpandedId(isExpanded ? null : ins.id)}
                      className="p-2 bg-white/5 hover:bg-white/10 rounded-[6px] text-tinta-3 hover:text-white transition-colors"
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-5 bg-black/20 border-t border-borde-sutil space-y-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-tinta-3 mb-2">
                      Plantilla de Jugadores ({ins.jugadores.length})
                    </h4>
                    {ins.jugadores.length === 0 ? (
                      <div className="p-4 rounded-[6px] border border-dashed border-borde text-center text-tinta-4 text-xs">
                        No se cargaron jugadores para este equipo.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {ins.jugadores.map((player) => (
                          <div
                            key={player.id}
                            className={`p-3 rounded-[6px] border flex items-center justify-between text-xs ${
                              player.es_capitan ? 'bg-acento/10 border-borde' : player.es_suplente ? 'bg-white/[0.01] border-borde-sutil opacity-70' : 'bg-white/[0.03] border-borde'
                            }`}
                          >
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="font-bold text-white">{player.identidad.nick || player.identidad.nombre || `Jugador #${player.orden}`}</span>
                                {player.es_capitan && <span className="px-1.5 py-0.2 rounded bg-amber-400/20 text-atencion font-bold text-[9px] uppercase">Capitán</span>}
                                {player.es_suplente && <span className="px-1.5 py-0.2 rounded bg-white/10 text-tinta-3 text-[9px] uppercase">Suplente</span>}
                              </div>
                              <div className="text-[11px] text-tinta-3 font-mono mt-0.5">
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
          <div className="bg-superficie border border-red-500/30 rounded-[6px] max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <XCircle className="text-vivo" size={20} /> Rechazar Inscripción de Equipo
            </h3>
            <form onSubmit={handleReject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-tinta-2 mb-1">Motivo del Rechazo</label>
                <textarea
                  value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Ej. Faltan jugadores titulares con ID verificado..."
                  className="w-full bg-fondo border border-borde rounded-[6px] px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500 h-24 resize-none"
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button type="button" onClick={() => setRejectingId(null)} className="px-4 py-2 bg-white/5 hover:bg-white/10 text-tinta-2 text-xs font-semibold rounded-[6px]">
                  Cancelar
                </button>
                <button type="submit" className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-[6px]">
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
