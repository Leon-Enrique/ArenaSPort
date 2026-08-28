'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ShieldAlert, CheckCircle2, AlertCircle, Eye,
  Image as ImageIcon, Loader2
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiDisputa, ApiEdicion, ApiPartida, ApiTorneo } from '@/lib/api-types';

export default function EdicionDisputasAdminPage() {
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [disputas, setDisputas] = useState<ApiDisputa[]>([]);
  const [partidaPorId, setPartidaPorId] = useState<Record<number, ApiPartida>>({});
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [veredictoNota, setVeredictoNota] = useState('');
  const [activeImageZoom, setActiveImageZoom] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [resolviendo, setResolviendo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = async () => {
    setLoading(true);
    try {
      const [t, ed, fases, todasDisputas] = await Promise.all([
        api.getTorneoById(torneoId), api.getEdicionById(edId), api.getFasesByEdicion(edId), api.getDisputasGlobal(),
      ]);
      setTorneo(t);
      setEdicion(ed);

      const partidasArrays = await Promise.all(fases.map(f => api.getPartidasByFase(String(f.id)).catch(() => [])));
      const partidasDeEdicion = partidasArrays.flat();
      const idsPartidas = new Set(partidasDeEdicion.map(p => p.id));

      setPartidaPorId(Object.fromEntries(partidasDeEdicion.map(p => [p.id, p])));
      const disputasDeEdicion = todasDisputas.filter(d => idsPartidas.has(d.partida_id));
      setDisputas(disputasDeEdicion);
      if (disputasDeEdicion[0]) setSelectedId(disputasDeEdicion[0].id);
    } catch {
      setError('No se pudieron cargar las disputas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, [torneoId, edId]);

  const selectedDisputa = disputas.find(d => d.id === selectedId) || null;
  const partida = selectedDisputa ? partidaPorId[selectedDisputa.partida_id] : null;
  const eqA = partida?.participaciones[0];
  const eqB = partida?.participaciones[1];

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleResolve = async (accion: 'walkover' | 'reprogramar', equipoGanadorId?: number) => {
    if (!selectedDisputa) return;
    setResolviendo(true);
    setError(null);
    try {
      await api.resolverDisputa(String(selectedDisputa.id), {
        resolucion: veredictoNota || 'Resuelto por el organizador.',
        accion,
        equipo_ganador_id: equipoGanadorId,
      });
      setVeredictoNota('');
      showToast('Disputa resuelta. Se actualizó el estado de la partida.');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo resolver la disputa.');
    } finally {
      setResolviendo(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando disputas...
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

      <div className="flex items-center gap-2 text-xs text-tinta-4">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">{torneo?.nombre}</Link>
        <span>/</span>
        <span className="text-tinta-2">Centro de Disputas</span>
      </div>

      <div>
        <span className="text-xs text-tinta-3">{edicion?.nombre}</span>
        <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
          <ShieldAlert className="text-vivo" /> Tribunal Arbitral y Resolución de Disputas
        </h1>
      </div>

      {error && (
        <div className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
          <AlertCircle size={15} /> <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-tinta-3 mb-2">Disputas Registradas ({disputas.length})</h3>

          {disputas.length === 0 && (
            <div className="glass-card p-8 text-center text-tinta-4 text-xs">
              No hay disputas registradas en esta edición.
            </div>
          )}

          {disputas.map(d => {
            const p = partidaPorId[d.partida_id];
            const a = p?.participaciones[0];
            const b = p?.participaciones[1];
            const isSelected = selectedId === d.id;
            return (
              <div
                key={d.id}
                onClick={() => setSelectedId(d.id)}
                className={`p-4 rounded-[6px] border transition-all cursor-pointer ${isSelected ? 'bg-acento/15 border-acento/50' : 'bg-superficie border-borde hover:border-white/20'}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-tinta-3">Partida #{d.partida_id}</span>
                  {d.estado === 'abierta' && <span className="text-[10px] font-bold text-vivo bg-red-500/15 border border-red-500/30 px-2 py-0.5 rounded-full">Abierta</span>}
                  {d.estado === 'resuelta' && <span className="text-[10px] font-bold text-ok bg-green-500/15 border border-green-500/30 px-2 py-0.5 rounded-full">Resuelta</span>}
                </div>
                <div className="text-sm font-bold text-white mb-1">
                  {a?.equipo.nombre || '—'} <span className="text-tinta-4 font-normal">vs</span> {b?.equipo.nombre || '—'}
                </div>
                <p className="text-xs text-tinta-3 line-clamp-2 mb-2">{d.motivo}</p>
                <div className="text-[10px] text-tinta-4">Registrada el {new Date(d.created_at).toLocaleString()}</div>
              </div>
            );
          })}
        </div>

        <div className="lg:col-span-7">
          {selectedDisputa ? (
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-borde-sutil">
                <div>
                  <span className="text-xs text-acento-claro font-semibold">Partida #{selectedDisputa.partida_id}</span>
                  <h2 className="text-lg font-black text-white mt-0.5">
                    {eqA?.equipo.nombre || '—'} vs {eqB?.equipo.nombre || '—'}
                  </h2>
                </div>
                {selectedDisputa.estado === 'resuelta' ? (
                  <div className="flex items-center gap-1 text-xs font-bold text-ok bg-green-500/15 border border-green-500/30 px-3 py-1 rounded-full">
                    <CheckCircle2 size={13} /> Caso Cerrado
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-xs font-bold text-atencion bg-amber-500/15 border border-amber-500/30 px-3 py-1 rounded-full">
                    <AlertCircle size={13} /> Dictamen Pendiente
                  </div>
                )}
              </div>

              <div className="p-4 rounded-[6px] bg-white/[0.02] border border-borde-sutil space-y-1.5">
                <span className="text-[11px] font-bold text-atencion uppercase tracking-wider block">Motivo de la disputa:</span>
                <p className="text-xs text-tinta-2 leading-relaxed italic">"{selectedDisputa.motivo}"</p>
              </div>

              {selectedDisputa.evidencia_url && (
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-tinta-3 mb-3 flex items-center gap-2">
                    <ImageIcon size={14} className="text-tinta-2" /> Evidencia Adjunta
                  </h3>
                  <div
                    onClick={() => setActiveImageZoom(selectedDisputa.evidencia_url)}
                    className="relative group rounded-[6px] overflow-hidden border border-borde aspect-video bg-black/40 cursor-zoom-in max-w-sm"
                  >
                    <img src={selectedDisputa.evidencia_url!} alt="Evidencia" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white text-xs font-bold gap-1 transition-opacity">
                      <Eye size={14} /> Ampliar
                    </div>
                  </div>
                </div>
              )}

              {selectedDisputa.resolucion && (
                <div className="p-4 rounded-[6px] bg-green-500/10 border border-green-500/30 text-xs text-green-300 space-y-1">
                  <div className="font-bold flex items-center gap-1.5 text-ok"><CheckCircle2 size={14} /> Dictamen:</div>
                  <p>{selectedDisputa.resolucion}</p>
                </div>
              )}

              {selectedDisputa.estado !== 'resuelta' && eqA && eqB && (
                <div className="space-y-4 pt-4 border-t border-borde-sutil">
                  <div>
                    <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Nota de Resolución</label>
                    <textarea
                      value={veredictoNota}
                      onChange={(e) => setVeredictoNota(e.target.value)}
                      placeholder="Motivo del fallo arbitral..."
                      className="w-full bg-fondo border border-borde rounded-[6px] px-3 py-2 text-xs text-white focus:outline-none focus:border-acento h-20 resize-none"
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <button
                      onClick={() => handleResolve('walkover', eqA.equipo.id)}
                      disabled={resolviendo}
                      className="px-3 py-2.5 bg-acento/30 hover:bg-acento border border-borde text-tinta-2 hover:text-white rounded-[6px] text-xs font-bold transition-all disabled:opacity-50"
                    >
                      ✓ Fallo a favor de {eqA.equipo.tag || eqA.equipo.nombre}
                    </button>
                    <button
                      onClick={() => handleResolve('walkover', eqB.equipo.id)}
                      disabled={resolviendo}
                      className="px-3 py-2.5 bg-acento/30 hover:bg-acento border border-borde text-tinta-2 hover:text-white rounded-[6px] text-xs font-bold transition-all disabled:opacity-50"
                    >
                      ✓ Fallo a favor de {eqB.equipo.tag || eqB.equipo.nombre}
                    </button>
                    <button
                      onClick={() => handleResolve('reprogramar')}
                      disabled={resolviendo}
                      className="px-3 py-2.5 bg-red-600/20 hover:bg-red-600 border border-red-500/30 text-vivo hover:text-white rounded-[6px] text-xs font-bold transition-all disabled:opacity-50"
                    >
                      Reprogramar Partida
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="glass-card p-12 text-center text-tinta-4">
              Selecciona una disputa de la lista para analizar el caso.
            </div>
          )}
        </div>
      </div>

      {activeImageZoom && (
        <div onClick={() => setActiveImageZoom(null)} className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-6 cursor-zoom-out">
          <img src={activeImageZoom} alt="Captura ampliada" className="max-h-[90vh] max-w-[90vw] rounded-[6px] object-contain shadow-2xl border border-white/20" />
        </div>
      )}
    </div>
  );
}
