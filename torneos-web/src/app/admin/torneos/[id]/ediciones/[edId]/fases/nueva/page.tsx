'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, Check, Layers, AlertCircle, Loader2, Plus, X } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiEdicion, ApiTorneo } from '@/lib/api-types';

export default function NuevaFasePage() {
  const router = useRouter();
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [orden, setOrden] = useState(1);
  const [loadingInicial, setLoadingInicial] = useState(true);

  useEffect(() => {
    Promise.all([api.getTorneoById(torneoId), api.getEdicionById(edId), api.getFasesByEdicion(edId)])
      .then(([t, ed, fs]) => { setTorneo(t); setEdicion(ed); setOrden(fs.length + 1); })
      .finally(() => setLoadingInicial(false));
  }, [torneoId, edId]);

  const [nombre, setNombre] = useState('');
  // Multi-equipo (battle royale) salio del producto junto con Free Fire y
  // CODM BR: el motor no genera caidas ni calcula su tabla. Queda fijo en
  // enfrentamiento directo hasta que ese motor exista.
  const modeloCompetencia = 'enfrentamiento_directo' as const;
  const [formato, setFormato] = useState<'eliminacion_simple' | 'eliminacion_doble' | 'round_robin' | 'suizo'>('eliminacion_doble');
  const [boDefault, setBoDefault] = useState<1 | 3 | 5>(3);
  const [tramosBo, setTramosBo] = useState<{ ronda: number; bo: 1 | 3 | 5 }[]>([]);
  const [cuposAvance, setCuposAvance] = useState(4);
  const [numGrupos, setNumGrupos] = useState(4);
  const [usarCorteSuizo, setUsarCorteSuizo] = useState(true);
  const [metaVictorias, setMetaVictorias] = useState(3);
  const [metaDerrotas, setMetaDerrotas] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const formatosDirectos = [
    { id: 'eliminacion_doble', nombre: 'Eliminación Doble', desc: 'Upper Bracket + Lower Bracket con gran final.' },
    { id: 'eliminacion_simple', nombre: 'Eliminación Simple', desc: 'Cuadro tradicional donde una derrota elimina al equipo.' },
    { id: 'round_robin', nombre: 'Fase de Grupos (Round Robin)', desc: 'Todos contra todos por puntos en cada grupo.' },
    { id: 'suizo', nombre: 'Sistema Suizo', desc: 'Enfrentamientos entre equipos con el mismo récord de victorias/derrotas.' },
  ];

  const addTramoBo = () => {
    setTramosBo(prev => {
      const ultimo = prev[prev.length - 1];
      return [...prev, { ronda: ultimo ? ultimo.ronda + 1 : 2, bo: 3 }];
    });
  };
  const updateTramoBo = (index: number, updates: Partial<{ ronda: number; bo: 1 | 3 | 5 }>) => {
    setTramosBo(prev => prev.map((t, i) => (i === index ? { ...t, ...updates } : t)));
  };
  const removeTramoBo = (index: number) => {
    setTramosBo(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const config: Record<string, any> = { bo: boDefault, cupos_avance: cuposAvance };
    if ((formato === 'eliminacion_simple' || formato === 'eliminacion_doble') && tramosBo.length > 0) {
      config.bo_por_ronda = tramosBo;
    }
    if (formato === 'round_robin') config.grupos = numGrupos;
    if (formato === 'suizo' && usarCorteSuizo) {
      config.meta_victorias = metaVictorias;
      config.meta_derrotas = metaDerrotas;
    }
    try {
      await api.createFase(edId, { orden, nombre: nombre.trim(), modelo_competencia: modeloCompetencia, formato, config });
      router.push(`/admin/torneos/${torneoId}/ediciones/${edId}/fases`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la fase.');
      setLoading(false);
    }
  };

  if (loadingInicial) {
    return (
      <div className="p-6 lg:p-8 max-w-3xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto">
      <Link
        href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases`}
        className="inline-flex items-center gap-2 text-sm text-white/40 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Volver a fases
      </Link>

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Configurar Nueva Fase</h1>
        <p className="text-sm text-white/40 mt-1">
          {torneo?.nombre} • {edicion?.nombre}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-[#13131f] border border-white/8 rounded-2xl p-6 sm:p-8 space-y-6">
        {/* Nombre & Orden */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="sm:col-span-3">
            <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">
              Nombre de la Fase *
            </label>
            <input
              type="text"
              required
              value={nombre}
              onChange={e => setNombre(e.target.value)}
              placeholder="Ej. Playoffs Upper Bracket, Fase de Grupos A..."
              className="w-full bg-white/5 border border-white/10 text-white placeholder-white/25 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">
              Orden / Etapa
            </label>
            <input
              type="number"
              min={1}
              value={orden}
              onChange={e => setOrden(parseInt(e.target.value) || 1)}
              className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm text-center focus:outline-none focus:border-violet-500 transition-all"
            />
          </div>
        </div>

        {/* Modelo Competitivo */}
        {/* Formatos disponibles */}
        <div>
          <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-3">
            Formato de Fase
          </label>
          <div className="space-y-2.5">
            {formatosDirectos.map((f) => (
              <label
                key={f.id}
                className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                  formato === f.id
                    ? 'border-violet-500 bg-violet-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <input
                  type="radio"
                  name="formato"
                  checked={formato === f.id}
                  onChange={() => setFormato(f.id as any)}
                  className="mt-1 accent-violet-600"
                />
                <div>
                  <p className="text-sm font-semibold text-white">{f.nombre}</p>
                  <p className="text-xs text-white/40 mt-0.5">{f.desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Configuración específica según formato */}
        <div className="pt-4 border-t border-white/8 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers size={15} className="text-cyan-400" />
            Parámetros de Juego
          </h3>

          {modeloCompetencia === 'enfrentamiento_directo' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">
                  Formato de Series (Best-Of)
                </label>
                <div className="flex gap-2">
                  {([1, 3, 5] as const).map(bo => (
                    <button
                      key={bo}
                      type="button"
                      onClick={() => setBoDefault(bo)}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all ${
                        boDefault === bo
                          ? 'border-cyan-500 bg-cyan-500/20 text-cyan-300'
                          : 'border-white/10 bg-white/5 text-white/50 hover:border-white/20'
                      }`}
                    >
                      BO{bo}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">
                  Cupos que clasifican a la sig. fase
                </label>
                <input
                  type="number"
                  min={1}
                  value={cuposAvance}
                  onChange={e => setCuposAvance(parseInt(e.target.value) || 1)}
                  className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-violet-500"
                />
              </div>

              {formato === 'round_robin' && (
                <div>
                  <label className="block text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">
                    Cantidad de Grupos
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={numGrupos}
                    onChange={e => setNumGrupos(parseInt(e.target.value) || 1)}
                    className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-violet-500"
                  />
                </div>
              )}
            </div>
          )}

          {(formato === 'eliminacion_simple' || formato === 'eliminacion_doble') && (
            <div className="pt-2 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white/70">
                  Escalar el Best-Of por ronda (opcional) — podés agregar tantos tramos como quieras
                </span>
                <button
                  type="button"
                  onClick={addTramoBo}
                  className="flex items-center gap-1 px-2.5 py-1.5 bg-violet-600/20 hover:bg-violet-600/40 border border-violet-500/30 text-violet-300 text-[11px] font-semibold rounded-lg transition-all"
                >
                  <Plus size={12} /> Agregar tramo
                </button>
              </div>

              {tramosBo.length === 0 && (
                <p className="text-[11px] text-white/40">Todas las rondas se juegan a BO{boDefault}.</p>
              )}

              {tramosBo.length > 0 && (
                <div className="space-y-2">
                  {tramosBo.map((tramo, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl p-2.5">
                      <span className="text-[11px] text-white/40 whitespace-nowrap">Desde ronda</span>
                      <input
                        type="number" min={1} value={tramo.ronda}
                        onChange={e => updateTramoBo(idx, { ronda: parseInt(e.target.value) || 1 })}
                        className="w-16 bg-[#0e0e1a] border border-white/10 text-white rounded-lg px-2 py-1.5 text-xs font-mono font-bold text-center focus:outline-none focus:border-violet-500"
                      />
                      <span className="text-[11px] text-white/40">→</span>
                      <div className="flex gap-1.5 flex-1">
                        {([1, 3, 5] as const).map(bo => (
                          <button
                            key={bo}
                            type="button"
                            onClick={() => updateTramoBo(idx, { bo })}
                            className={`flex-1 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                              tramo.bo === bo
                                ? 'border-cyan-500 bg-cyan-500/20 text-cyan-300'
                                : 'border-white/10 bg-white/5 text-white/50 hover:border-white/20'
                            }`}
                          >
                            BO{bo}
                          </button>
                        ))}
                      </div>
                      <button
                        type="button"
                        onClick={() => removeTramoBo(idx)}
                        className="text-white/30 hover:text-rose-400 p-1"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                  <p className="text-[10px] text-white/30">
                    Ej: BO{boDefault} hasta ronda {tramosBo[0].ronda - 1 || 1}, luego {tramosBo.map(t => `BO${t.bo} desde ronda ${t.ronda}`).join(', ')}.
                    {formato === 'eliminacion_doble' && ' En eliminación doble, la ronda 1 es la primera de la llave alta y la gran final cae en la última ronda de la fase.'}
                  </p>
                </div>
              )}
            </div>
          )}

          {formato === 'suizo' && (
            <div className="pt-2 space-y-3">
              <label className="flex items-center gap-2 text-xs font-semibold text-white/70 cursor-pointer">
                <input
                  type="checkbox" checked={usarCorteSuizo}
                  onChange={e => setUsarCorteSuizo(e.target.checked)}
                  className="rounded bg-white/5 border-white/20 text-violet-600 focus:ring-0"
                />
                Suizo con corte (estilo M7/MPL): clasifica al llegar a N victorias, elimina al llegar a N derrotas
              </label>
              {usarCorteSuizo && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">Victorias para clasificar</label>
                    <input
                      type="number" min={1} value={metaVictorias}
                      onChange={e => setMetaVictorias(parseInt(e.target.value) || 1)}
                      className="w-full bg-white/5 border border-white/10 text-emerald-300 rounded-xl px-4 py-2 text-sm font-mono font-bold focus:outline-none focus:border-violet-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">Derrotas para eliminar</label>
                    <input
                      type="number" min={1} value={metaDerrotas}
                      onChange={e => setMetaDerrotas(parseInt(e.target.value) || 1)}
                      className="w-full bg-white/5 border border-white/10 text-rose-300 rounded-xl px-4 py-2 text-sm font-mono font-bold focus:outline-none focus:border-violet-500"
                    />
                  </div>
                </div>
              )}
              {!usarCorteSuizo && (
                <p className="text-[11px] text-white/40">Sin corte: todos los equipos juegan todas las rondas que generes, sin clasificar ni eliminar automáticamente.</p>
              )}
            </div>
          )}

        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={15} /> <span>{error}</span>
          </div>
        )}

        {/* Buttons */}
        <div className="flex items-center justify-end gap-3 pt-6 border-t border-white/8">
          <Link
            href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases`}
            className="px-5 py-2.5 rounded-xl border border-white/10 text-white/60 hover:text-white text-sm transition-colors"
          >
            Cancelar
          </Link>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-violet-600 to-cyan-600 hover:opacity-90 text-white text-sm font-semibold rounded-xl shadow-lg transition-all disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
            Crear Fase
          </button>
        </div>
      </form>
    </div>
  );
}
