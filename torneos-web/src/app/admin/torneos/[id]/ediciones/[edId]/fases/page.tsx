'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Swords, Plus, Play, CheckCircle2, Clock,
  Layers, ChevronRight, BarChart3, Loader2, AlertCircle, Lock, Trophy, Undo2, ListFilter, Trash2
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiEdicion, ApiFase, ApiPartida, ApiTorneo } from '@/lib/api-types';

const FORMATO_LABELS: Record<string, string> = {
  round_robin: 'Round Robin (Todos contra todos)',
  eliminacion_simple: 'Eliminación Simple (Brackets)',
  eliminacion_doble: 'Eliminación Doble (Upper / Lower)',
  suizo: 'Sistema Suizo',
};

const ESTADO_BADGE: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  cerrada: { label: 'Cerrada', color: 'bg-green-500/15 text-ok border-green-500/30', icon: <CheckCircle2 size={12} /> },
  en_curso: { label: 'En Curso', color: 'bg-amber-500/15 text-atencion border-amber-500/30', icon: <Play size={12} /> },
  sorteada: { label: 'Sorteada', color: 'bg-cyan-500/15 text-tinta-2 border-cyan-500/30', icon: <Play size={12} /> },
  pendiente: { label: 'Pendiente de sorteo', color: 'bg-white/10 text-tinta-3 border-borde', icon: <Clock size={12} /> },
};

const RESUELTOS = new Set(['confirmada', 'walkover', 'bye']);

/** Cuántos equipos ya llegaron a `metaVictorias` en una fase suiza con
 * corte — el clasificado real de un suizo tipo M7 no es "top N de la
 * tabla", es "quien llegó a N victorias", así que se cuenta directo de
 * las partidas en vez de reusar la lógica de tabla por puntos. */
function contarClasificadosSuizo(partidas: ApiPartida[], metaVictorias: number): number {
  const victorias = new Map<number, number>();
  for (const p of partidas) {
    if (!RESUELTOS.has(p.estado)) continue;
    for (const part of p.participaciones) {
      if (part.es_ganador) {
        victorias.set(part.equipo.id, (victorias.get(part.equipo.id) || 0) + 1);
      }
    }
  }
  return Array.from(victorias.values()).filter(v => v >= metaVictorias).length;
}

export default function FasesAdminPage() {
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [fases, setFases] = useState<ApiFase[]>([]);
  const [partidasPorFase, setPartidasPorFase] = useState<Record<number, ApiPartida[]>>({});
  const [loading, setLoading] = useState(true);
  const [sorteando, setSorteando] = useState<number | null>(null);
  const [generandoRonda, setGenerandoRonda] = useState<number | null>(null);
  const [cerrando, setCerrando] = useState<number | null>(null);
  const [reseteando, setReseteando] = useState<number | null>(null);
  const [eliminandoFase, setEliminandoFase] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sorteoAvanzado, setSorteoAvanzado] = useState<{
    faseId: number; faseOrigenId: number | ''; cuposPorGrupo: string; rondaOrigen: string;
  } | null>(null);

  const cargar = () => {
    setLoading(true);
    Promise.all([api.getTorneoById(torneoId), api.getEdicionById(edId), api.getFasesByEdicion(edId)])
      .then(async ([t, ed, fs]) => {
        setTorneo(t);
        setEdicion(ed);
        setFases(fs);
        const partidas = await Promise.all(fs.map(f => api.getPartidasByFase(String(f.id)).catch(() => [])));
        setPartidasPorFase(Object.fromEntries(fs.map((f, i) => [f.id, partidas[i]])));
      })
      .finally(() => setLoading(false));
  };

  useEffect(cargar, [torneoId, edId]);

  const handleSortear = async (faseId: number) => {
    setError(null);
    setSorteando(faseId);
    try {
      await api.sortearFase(edId, String(faseId));
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo sortear la fase.');
    } finally {
      setSorteando(null);
    }
  };

  const handleSiguienteRonda = async (faseId: number) => {
    setError(null);
    setGenerandoRonda(faseId);
    try {
      await api.siguienteRondaSuiza(edId, String(faseId));
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo generar la siguiente ronda.');
    } finally {
      setGenerandoRonda(null);
    }
  };

  const handleCerrar = async (faseId: number) => {
    setError(null);
    setCerrando(faseId);
    try {
      await api.cerrarFase(edId, String(faseId));
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cerrar la fase.');
    } finally {
      setCerrando(null);
    }
  };

  const handleResetearSorteo = async (faseId: number) => {
    if (!window.confirm('¿Resetear el sorteo de esta fase? Se van a borrar sus partidas y vuelve a "pendiente" para sortear de nuevo. Solo funciona si ninguna partida tuvo actividad todavía.')) {
      return;
    }
    setError(null);
    setReseteando(faseId);
    try {
      await api.resetearSorteo(edId, String(faseId));
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo resetear el sorteo.');
    } finally {
      setReseteando(null);
    }
  };

  const handleEliminarFase = async (faseId: number, nombre: string) => {
    if (!window.confirm(`¿Eliminar la fase "${nombre}"? Se borra por completo (no solo el sorteo) — solo funciona si ninguna partida tuvo actividad todavía. No se puede deshacer.`)) {
      return;
    }
    setError(null);
    setEliminandoFase(faseId);
    try {
      await api.eliminarFase(edId, String(faseId));
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo eliminar la fase.');
    } finally {
      setEliminandoFase(null);
    }
  };

  const handleSortearDesdeAnterior = async () => {
    if (!sorteoAvanzado) return;
    const { faseId, faseOrigenId, cuposPorGrupo, rondaOrigen } = sorteoAvanzado;
    if (!faseOrigenId) {
      setError('Elegí de qué fase salen los clasificados.');
      return;
    }
    setError(null);
    setSorteando(faseId);
    try {
      await api.sortearFaseDesdeAnterior(edId, String(faseId), {
        fase_origen_id: Number(faseOrigenId),
        cupos_por_grupo: cuposPorGrupo ? parseInt(cuposPorGrupo) : undefined,
        ronda_origen: rondaOrigen ? parseInt(rondaOrigen) : undefined,
      });
      setSorteoAvanzado(null);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo sortear desde la fase anterior.');
    } finally {
      setSorteando(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando fases...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-2 text-xs text-tinta-4 mb-6">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">{torneo?.nombre}</Link>
        <span>/</span>
        <span className="text-tinta-2">Fases y Etapas</span>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <span className="text-xs text-tinta-3">{edicion?.nombre}</span>
          <h1 className="text-2xl font-bold text-white">Estructura y Fases del Torneo</h1>
        </div>
        <Link
          href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases/nueva`}
          className="flex items-center gap-2 px-4 py-2.5 bg-acento hover:from-violet-500 hover:to-cyan-500 text-white text-sm font-semibold rounded-[6px] transition-all"
        >
          <Plus size={16} /> Agregar Fase
        </Link>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
          <AlertCircle size={15} /> <span>{error}</span>
        </div>
      )}

      <div className="space-y-4">
        {fases.length === 0 && (
          <div className="bg-superficie border border-borde rounded-[6px] p-12 text-center text-tinta-4">
            <Layers size={40} className="mx-auto mb-3 opacity-30 text-acento-claro" />
            <p className="text-base font-semibold text-tinta-2">No hay fases configuradas aún</p>
            <Link
              href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases/nueva`}
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-acento hover:bg-acento text-white text-xs font-semibold rounded-[6px]"
            >
              <Plus size={14} /> Crear primera fase
            </Link>
          </div>
        )}

        {fases.map((fase) => {
          const badge = ESTADO_BADGE[fase.estado] ?? ESTADO_BADGE['pendiente'];
          const partidas = partidasPorFase[fase.id] || [];
          const completadas = partidas.filter(p => p.estado === 'confirmada' || p.estado === 'walkover' || p.estado === 'bye').length;

          return (
            <div key={fase.id} className="bg-superficie border border-borde rounded-[6px] p-6 hover:border-white/20 transition-all group">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-[6px] bg-acento/10 border border-borde flex items-center justify-center font-bold text-acento-claro text-sm flex-shrink-0">
                    #{fase.orden}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-bold text-white">{fase.nombre}</h3>
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badge.color}`}>
                        {badge.icon} {badge.label}
                      </span>
                    </div>
                    <p className="text-xs text-tinta-3">{FORMATO_LABELS[fase.formato] ?? fase.formato}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {fase.estado === 'pendiente' && (
                    <button
                      onClick={() => handleSortear(fase.id)}
                      disabled={sorteando === fase.id}
                      title="Arma la fase con TODOS los equipos inscritos y aprobados en la edición."
                      className="flex items-center gap-1.5 px-3 py-2 bg-emerald-600/20 hover:bg-emerald-600/40 border border-emerald-500/30 text-ok text-xs font-semibold rounded-[6px] transition-all disabled:opacity-50"
                    >
                      {sorteando === fase.id ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                      Sortear (todos los inscritos)
                    </button>
                  )}
                  {fase.estado === 'pendiente' && fases.length > 1 && (
                    <button
                      onClick={() => setSorteoAvanzado(
                        sorteoAvanzado?.faseId === fase.id
                          ? null
                          : { faseId: fase.id, faseOrigenId: fases.find(f => f.orden < fase.orden)?.id ?? '', cuposPorGrupo: '', rondaOrigen: '' }
                      )}
                      title="Arma la fase solo con los equipos que clasificaron de otra fase ya jugada."
                      className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/40 border border-cyan-500/30 text-tinta-2 text-xs font-semibold rounded-[6px] transition-all"
                    >
                      <ListFilter size={13} /> Con clasificados de otra fase
                    </button>
                  )}
                  {(fase.estado === 'sorteada' || fase.estado === 'en_curso') && completadas === 0 && (
                    <button
                      onClick={() => handleResetearSorteo(fase.id)}
                      disabled={reseteando === fase.id}
                      title="Borra las partidas de esta fase (nadie jugó nada todavía) y la vuelve a 'pendiente' para sortear de nuevo."
                      className="flex items-center gap-1.5 px-3 py-2 bg-rose-600/15 hover:bg-rose-600/30 border border-rose-500/30 text-vivo text-xs font-semibold rounded-[6px] transition-all disabled:opacity-50"
                    >
                      {reseteando === fase.id ? <Loader2 size={13} className="animate-spin" /> : <Undo2 size={13} />}
                      Resetear Sorteo
                    </button>
                  )}
                  {(fase.estado === 'pendiente' || ((fase.estado === 'sorteada' || fase.estado === 'en_curso') && completadas === 0)) && (
                    <button
                      onClick={() => handleEliminarFase(fase.id, fase.nombre)}
                      disabled={eliminandoFase === fase.id}
                      title="Borra esta fase por completo — solo funciona si ninguna partida tuvo actividad todavía."
                      className="flex items-center gap-1.5 px-3 py-2 bg-rose-600/15 hover:bg-rose-600/30 border border-rose-500/30 text-vivo text-xs font-semibold rounded-[6px] transition-all disabled:opacity-50"
                    >
                      {eliminandoFase === fase.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                      Eliminar Fase
                    </button>
                  )}
                  {fase.formato === 'suizo' && (fase.estado === 'sorteada' || fase.estado === 'en_curso') && (
                    <button
                      onClick={() => handleSiguienteRonda(fase.id)}
                      disabled={generandoRonda === fase.id}
                      className="flex items-center gap-1.5 px-3 py-2 bg-cyan-600/20 hover:bg-cyan-600/40 border border-cyan-500/30 text-tinta-2 text-xs font-semibold rounded-[6px] transition-all disabled:opacity-50"
                    >
                      {generandoRonda === fase.id ? <Loader2 size={13} className="animate-spin" /> : <ChevronRight size={13} />}
                      Siguiente Ronda
                    </button>
                  )}
                  {(fase.estado === 'sorteada' || fase.estado === 'en_curso') && partidas.length > 0 && completadas === partidas.length && (
                    <button
                      onClick={() => handleCerrar(fase.id)}
                      disabled={cerrando === fase.id}
                      title="Marca la fase como terminada y habilita sacar sus clasificados para la siguiente fase."
                      className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-indigo-300 text-xs font-semibold rounded-[6px] transition-all disabled:opacity-50"
                    >
                      {cerrando === fase.id ? <Loader2 size={13} className="animate-spin" /> : <Lock size={13} />}
                      Cerrar Fase
                    </button>
                  )}
                  <Link
                    href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases/${fase.id}/partidas`}
                    className="flex items-center gap-1.5 px-3 py-2 bg-acento/20 hover:bg-acento/40 border border-borde text-acento-claro text-xs font-semibold rounded-[6px] transition-all"
                  >
                    <Swords size={13} /> Partidas ({completadas}/{partidas.length})
                  </Link>
                  <Link
                    href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases/${fase.id}/tabla`}
                    className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/10 border border-borde text-tinta-2 hover:text-white text-xs rounded-[6px] transition-all"
                  >
                    <BarChart3 size={13} /> Tabla / Posiciones
                  </Link>
                </div>
              </div>

              {sorteoAvanzado?.faseId === fase.id && (() => {
                const faseOrigen = fases.find(f => f.id === sorteoAvanzado.faseOrigenId);
                return (
                  <div className="mb-4 p-4 rounded-[6px] bg-cyan-500/5 border border-cyan-500/20 space-y-3">
                    <p className="text-xs font-semibold text-tinta-2">Sortear con los clasificados de otra fase</p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-[11px] text-tinta-3 mb-1">Fase de origen</label>
                        <select
                          value={sorteoAvanzado.faseOrigenId}
                          onChange={e => setSorteoAvanzado(s => s && { ...s, faseOrigenId: e.target.value ? Number(e.target.value) : '' })}
                          className="w-full bg-fondo border border-borde text-white rounded-[4px] px-3 py-2 text-xs focus:outline-none focus:border-cyan-500"
                        >
                          <option value="">Elegir...</option>
                          {fases.filter(f => f.id !== fase.id).map(f => (
                            <option key={f.id} value={f.id}>#{f.orden} {f.nombre} ({FORMATO_LABELS[f.formato] ?? f.formato})</option>
                          ))}
                        </select>
                      </div>
                      {faseOrigen && (faseOrigen.formato === 'round_robin' || faseOrigen.formato === 'suizo') && (
                        <div>
                          <label className="block text-[11px] text-tinta-3 mb-1">Cuántos clasifican</label>
                          <input
                            type="number" min={1}
                            value={sorteoAvanzado.cuposPorGrupo}
                            onChange={e => setSorteoAvanzado(s => s && { ...s, cuposPorGrupo: e.target.value })}
                            placeholder={String(faseOrigen.config?.cupos_avance ?? '8')}
                            className="w-full bg-fondo border border-borde text-white rounded-[4px] px-3 py-2 text-xs font-mono focus:outline-none focus:border-cyan-500"
                          />
                          {faseOrigen.formato === 'suizo' && faseOrigen.config?.meta_victorias && (
                            <p className="text-[10px] text-tinta-4 mt-1">
                              Esta fase suiza clasifica a quien llega a {faseOrigen.config.meta_victorias} victorias — poné ese número exacto de equipos acá.
                            </p>
                          )}
                        </div>
                      )}
                      {faseOrigen && faseOrigen.formato === 'eliminacion_simple' && (
                        <div>
                          <label className="block text-[11px] text-tinta-3 mb-1">Ronda de origen (toma los ganadores de esa ronda)</label>
                          <input
                            type="number" min={1}
                            value={sorteoAvanzado.rondaOrigen}
                            onChange={e => setSorteoAvanzado(s => s && { ...s, rondaOrigen: e.target.value })}
                            className="w-full bg-fondo border border-borde text-white rounded-[4px] px-3 py-2 text-xs font-mono focus:outline-none focus:border-cyan-500"
                          />
                        </div>
                      )}
                    </div>
                    {faseOrigen && faseOrigen.formato !== 'round_robin' && faseOrigen.formato !== 'suizo' && faseOrigen.formato !== 'eliminacion_simple' && (
                      <p className="text-[11px] text-atencion/80">
                        Todavía no se pueden sacar clasificados automáticos de una fase &quot;{FORMATO_LABELS[faseOrigen.formato] ?? faseOrigen.formato}&quot; — hay que re-inscribir a mano.
                      </p>
                    )}
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleSortearDesdeAnterior}
                        disabled={sorteando === fase.id || !faseOrigen}
                        className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-[4px] disabled:opacity-50"
                      >
                        {sorteando === fase.id ? 'Sorteando...' : 'Confirmar Sorteo'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setSorteoAvanzado(null)}
                        className="px-3.5 py-1.5 bg-white/5 hover:bg-white/10 text-tinta-3 hover:text-white text-xs rounded-[4px]"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                );
              })()}

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-borde-sutil text-xs">
                <div>
                  <span className="text-tinta-4 block">Modelo Competitivo</span>
                  <span className="text-tinta-2 font-medium capitalize">{fase.modelo_competencia.replace('_', ' ')}</span>
                </div>
                <div>
                  <span className="text-tinta-4 block">Partidas Jugadas</span>
                  <span className="text-tinta-2 font-medium">{completadas} de {partidas.length} listas</span>
                </div>
                {(fase.formato === 'round_robin' || fase.formato === 'suizo') && (
                  <div>
                    <span className="text-tinta-4 block">Clasifican a la sig. fase</span>
                    <span className="text-ok font-bold flex items-center gap-1">
                      <Trophy size={12} />
                      {fase.formato === 'suizo' && fase.config?.meta_victorias
                        ? fase.estado === 'cerrada'
                          ? `${contarClasificadosSuizo(partidas, fase.config.meta_victorias)} equipos`
                          : `hasta ${fase.config.meta_victorias} victorias`
                        : `${fase.config?.cupos_avance ?? '—'} equipos`}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-end">
                  <Link
                    href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases/${fase.id}/partidas`}
                    className="text-acento-claro hover:text-acento-claro flex items-center gap-1 font-semibold group-hover:translate-x-1 transition-all"
                  >
                    Administrar Llaves <ChevronRight size={14} />
                  </Link>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
