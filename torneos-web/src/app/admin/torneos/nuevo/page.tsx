'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Trophy, Gamepad2, Users, Calendar, ArrowLeft, Swords,
  Layers, Sparkles, Shield, CheckCircle2, ChevronRight,
  Plus, Trash2, ArrowRight, Check, Flame, Zap, Settings2, AlertCircle, X
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { Juego } from '@/types';

function siguientePotenciaDeDos(n: number): number {
  let tamano = 1;
  while (tamano < n) tamano *= 2;
  return tamano;
}

/** Cuántas rondas tiene un cuadro de eliminación simple de n equipos —
 * espejo exacto de `siguiente_potencia_de_dos` + log2 del backend. */
function totalRondasEliminacionSimple(n: number): number {
  if (n < 2) return 1;
  return Math.log2(siguientePotenciaDeDos(n));
}

/** Cuántas rondas tiene un cuadro de eliminación doble de n equipos —
 * espejo del algoritmo de `app/domain/formatos/eliminacion_doble.py`
 * (llave alta + llave baja intercalada + gran final), pero trabajando
 * solo con conteos en vez de armar la llave completa. */
function totalRondasEliminacionDoble(n: number): number {
  if (n < 3) return 1;

  const tamano = siguientePotenciaDeDos(n);
  const rondasAlta = Math.log2(tamano);
  const byesIniciales = tamano - n;

  let activos = tamano;
  const perdedoresPorRonda: Record<number, number> = {};
  for (let r = 1; r <= rondasAlta; r++) {
    const partidos = activos / 2;
    const byesEsteRound = r === 1 ? byesIniciales : 0;
    perdedoresPorRonda[r] = partidos - byesEsteRound;
    activos = partidos;
  }

  const emparejar = (entrantes: number) => Math.floor(entrantes / 2) + (entrantes % 2);

  let rondaBaja = 1;
  let espera = emparejar(perdedoresPorRonda[1]);

  for (let r = 2; r <= rondasAlta; r++) {
    if (r >= 3) {
      rondaBaja += 1;
      espera = emparejar(espera);
    }
    rondaBaja += 1;
    espera = emparejar(espera + perdedoresPorRonda[r]);
  }

  while (espera > 1) {
    rondaBaja += 1;
    espera = emparejar(espera);
  }

  return rondaBaja + 1;
}

function totalRondas(formato: string, equiposEntran: number): number {
  return formato === 'eliminacion_doble'
    ? totalRondasEliminacionDoble(equiposEntran)
    : totalRondasEliminacionSimple(equiposEntran);
}

interface FaseConfig {
  id: string;
  nombre: string;
  formato: 'round_robin' | 'eliminacion_simple' | 'eliminacion_doble' | 'suizo';
  equiposEntran: number;
  numGrupos?: number;
  equiposPorGrupo?: number;
  clasificadosPorGrupo?: number;
  cuposAvance: number;
  bo: 1 | 3 | 5;
  tramosBo?: { ronda: number; bo: 1 | 3 | 5 }[];
}

export default function NuevoTorneoPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);

  const [juegosReales, setJuegosReales] = useState<Juego[]>([]);
  useEffect(() => { api.getJuegos().then(setJuegosReales).catch(() => {}); }, []);

  // Paso 1: Juego y Nombre
  const [juegoCodigo, setJuegoCodigo] = useState<'mlbb' | 'free_fire' | 'codm'>('mlbb');
  const [nombreTorneo, setNombreTorneo] = useState('Copa Latam Mobile Legends 2026');
  const [descripcion, setDescripcion] = useState('Torneo oficial con fase eliminatoria y premios para los mejores equipos.');
  
  // Paso 2: Total de Equipos y Fases Encadenadas
  // totalEquipos = siempre fases[0].equiposEntran (fuente de verdad)
  const [plantillaActiva, setPlantillaActiva] = useState<string>('32');

  const [fases, setFases] = useState<FaseConfig[]>([
    {
      id: 'fase-1',
      nombre: 'Cuadro Principal de Brackets (32 Slots)',
      formato: 'eliminacion_simple',
      equiposEntran: 32,
      cuposAvance: 1,
      bo: 1
    }
  ]);

  // Paso 3: Fechas y Premios
  const [fechaInicio, setFechaInicio] = useState('2026-09-01');
  const [bolsaPremios, setBolsaPremios] = useState('$1,500 USD');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [creadoExitoso, setCreadoExitoso] = useState(false);

  // totalEquipos siempre derivado de la primera fase
  const totalEquipos = fases[0]?.equiposEntran ?? 32;

  // ────────────────────────────────────────────
  // PLANTILLAS RÁPIDAS: 8, 16, 32, 64, 128, 40
  // ────────────────────────────────────────────
  const aplicarPlantilla = (tipo: '8' | '16' | '32' | '64' | '128' | '40_grupos') => {
    setPlantillaActiva(tipo);

    if (tipo === '8') {
      setNombreTorneo('Torneo Rápido (8 Equipos)');
      setFases([
        {
          id: 'fase-1',
          nombre: 'Playoffs de Eliminación Simple (Cuartos ➔ Semis ➔ Final)',
          formato: 'eliminacion_simple',
          equiposEntran: 8,
          cuposAvance: 1,
          bo: 1
        }
      ]);
    } else if (tipo === '16') {
      setNombreTorneo('Copa Regional (16 Equipos)');
      setFases([
        {
          id: 'fase-1',
          nombre: 'Bracket de Eliminación Directa (4 Rondas)',
          formato: 'eliminacion_simple',
          equiposEntran: 16,
          cuposAvance: 1,
          bo: 1
        }
      ]);
    } else if (tipo === '32') {
      setNombreTorneo('Copa Continental (32 Equipos)');
      setFases([
        {
          id: 'fase-1',
          nombre: 'Bracket de Eliminación Directa (5 Rondas)',
          formato: 'eliminacion_simple',
          equiposEntran: 32,
          cuposAvance: 1,
          bo: 1
        }
      ]);
    } else if (tipo === '64') {
      setNombreTorneo('Gran Open Nacional (64 Equipos)');
      setFases([
        {
          id: 'fase-1',
          nombre: 'Mega Bracket de Eliminación Directa (6 Rondas)',
          formato: 'eliminacion_simple',
          equiposEntran: 64,
          cuposAvance: 1,
          bo: 1
        }
      ]);
    } else if (tipo === '128') {
      setNombreTorneo('Torneo Masivo Internacional (128 Equipos)');
      setFases([
        {
          id: 'fase-1',
          nombre: 'Macro Bracket Eliminatorio (7 Rondas)',
          formato: 'eliminacion_simple',
          equiposEntran: 128,
          cuposAvance: 1,
          bo: 1
        }
      ]);
    } else if (tipo === '40_grupos') {
      setNombreTorneo('Copa 40 Equipos (Grupos + Llaves + Doble Final)');
      setFases([
        {
          id: 'fase-1',
          nombre: 'Fase 1: 8 Grupos de 5 Equipos (Round Robin)',
          formato: 'round_robin',
          equiposEntran: 40,
          numGrupos: 8,
          equiposPorGrupo: 5,
          clasificadosPorGrupo: 2,
          cuposAvance: 16,
          bo: 1
        },
        {
          id: 'fase-2',
          nombre: 'Fase 2: Eliminatoria Directa (16 a 8 Equipos)',
          formato: 'eliminacion_simple',
          equiposEntran: 16,
          cuposAvance: 8,
          bo: 1
        },
        {
          id: 'fase-3',
          nombre: 'Fase 3: Gran Final Doble Eliminación (Top 8)',
          formato: 'eliminacion_doble',
          equiposEntran: 8,
          cuposAvance: 1,
          bo: 1
        }
      ]);
    }
  };

  // Añadir nueva fase al final de la cadena
  const handleAddFase = () => {
    const lastFase = fases[fases.length - 1];
    const incomingTeams = lastFase ? lastFase.cuposAvance : 8;
    const newIdx = fases.length + 1;

    setFases([
      ...fases,
      {
        id: `fase-${Date.now()}`,
        nombre: `Fase ${newIdx}: Playoffs (${incomingTeams} Equipos)`,
        formato: 'eliminacion_doble',
        equiposEntran: incomingTeams,
        cuposAvance: Math.max(1, Math.floor(incomingTeams / 2)),
        bo: 1
      }
    ]);
  };

  // Eliminar fase
  const handleRemoveFase = (index: number) => {
    if (fases.length <= 1) {
      alert('El torneo debe tener al menos una fase.');
      return;
    }
    const newFases = fases.filter((_, i) => i !== index);
    for (let i = 1; i < newFases.length; i++) {
      newFases[i].equiposEntran = newFases[i - 1].cuposAvance;
    }
    setFases(newFases);
  };

  // Modificar fase
  const updateFase = (index: number, updates: Partial<FaseConfig>) => {
    const updated = [...fases];
    updated[index] = { ...updated[index], ...updates };

    if (updated[index].formato === 'round_robin') {
      const numG = updated[index].numGrupos || 8;
      const clasifPorG = updated[index].clasificadosPorGrupo || 2;
      updated[index].cuposAvance = numG * clasifPorG;
    }

    if (updated[index + 1]) {
      updated[index + 1].equiposEntran = updated[index].cuposAvance;
    }

    setFases(updated);
  };

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    if (step === 1 && !nombreTorneo.trim()) {
      alert('Por favor escribe un nombre para el torneo.');
      return;
    }
    if (step === 2) {
      // Validar que la cadena de fases sea coherente
      for (let i = 0; i < fases.length - 1; i++) {
        if (fases[i].cuposAvance > fases[i + 1].equiposEntran) {
          alert(`Error: La Fase ${i + 1} clasifica ${fases[i].cuposAvance} equipos, pero la Fase ${i + 2} solo recibe ${fases[i + 1].equiposEntran}. Revisa los cupos.`);
          return;
        }
        if (fases[i].cuposAvance <= 0) {
          alert(`La Fase ${i + 1} debe clasificar al menos 1 equipo.`);
          return;
        }
      }
      // Advertir si cuposAvance no es potencia de 2 para elim simple/doble
      fases.forEach((f, i) => {
        if ((f.formato === 'eliminacion_simple' || f.formato === 'eliminacion_doble') && f.equiposEntran > 1) {
          const esPotencia2 = (f.equiposEntran & (f.equiposEntran - 1)) === 0;
          if (!esPotencia2) {
            console.warn(`Fase ${i + 1}: ${f.equiposEntran} equipos no es potencia de 2 para bracket de eliminación.`);
          }
        }
      });
    }
    if (step < 3) setStep((step + 1) as any);
  };

  const [errorSubmit, setErrorSubmit] = useState<string | null>(null);

  const handleCrearTorneo = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorSubmit(null);
    const juegoObj = juegosReales.find(j => j.codigo === juegoCodigo);
    if (!juegoObj) {
      setErrorSubmit('No se pudo cargar el catalogo de juegos. Revisa que el backend este corriendo.');
      return;
    }

    setIsSubmitting(true);
    try {
      const torneo = await api.createTorneo({ nombre: nombreTorneo, descripcion });
      const edicion = await api.createEdicion({
        torneo_id: torneo.id,
        juego_id: Number(juegoObj.id),
        numero: 1,
        nombre: `${nombreTorneo} - Edicion 1`,
        max_equipos: totalEquipos,
        fecha_inicio: fechaInicio || undefined,
        bolsa_premios: bolsaPremios || undefined,
      });
      await api.cambiarEstadoEdicion(String(edicion.id), 'inscripciones_abiertas');

      for (const [i, f] of fases.entries()) {
        const config: Record<string, any> = { cupos_avance: f.cuposAvance, bo: f.bo };
        if (f.formato === 'round_robin') {
          config.grupos = f.numGrupos || 8;
          config.clasificados_por_grupo = f.clasificadosPorGrupo || 2;
        }
        if ((f.formato === 'eliminacion_simple' || f.formato === 'eliminacion_doble') && f.tramosBo && f.tramosBo.length > 0) {
          config.bo_por_ronda = f.tramosBo;
        }
        await api.createFase(String(edicion.id), {
          orden: i + 1,
          nombre: f.nombre,
          modelo_competencia: juegoObj.modeloCompetenciaDefault,
          formato: f.formato,
          config,
        });
      }

      setCreadoExitoso(true);
      setTimeout(() => { router.push(`/admin/torneos/${torneo.id}`); }, 500);
    } catch (err) {
      setErrorSubmit(err instanceof ApiError ? err.message : 'No se pudo crear el torneo. Intenta de nuevo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <span className="text-purple-400 font-semibold">Constructor de Torneos</span>
      </div>

      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-950/80 border border-purple-800 text-purple-300 text-xs font-semibold mb-2">
          <Sparkles size={13} />
          <span>Constructor Multi-Fase</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-white">Crear Nuevo Torneo</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Diseña las etapas de tu torneo (8, 16, 32, 64, 128 o 40 equipos) y encadena grupos, sistema suizo y playoffs.
        </p>
      </div>

      {/* Steps Pill */}
      <div className="grid grid-cols-3 gap-2 bg-[#0e101d] p-2 rounded-2xl border border-slate-800 text-xs font-bold">
        <button
          onClick={() => setStep(1)}
          className={`py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-all ${
            step === 1
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : step > 1
              ? 'bg-purple-950/40 text-purple-300 border border-purple-800/40'
              : 'text-slate-500'
          }`}
        >
          <span>1. Juego y Nombre</span>
          {step > 1 && <Check size={14} className="text-emerald-400" />}
        </button>

        <button
          onClick={() => step > 1 && setStep(2)}
          className={`py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-all ${
            step === 2
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : step > 2
              ? 'bg-purple-950/40 text-purple-300 border border-purple-800/40'
              : 'text-slate-500'
          }`}
        >
          <span>2. Fases y Equipos</span>
          {step > 2 && <Check size={14} className="text-emerald-400" />}
        </button>

        <button
          onClick={() => step > 2 && setStep(3)}
          className={`py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-all ${
            step === 3
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'text-slate-500'
          }`}
        >
          <span>3. Premios y Publicar</span>
        </button>
      </div>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* PASO 1: SELECCIONA EL JUEGO Y EL NOMBRE DEL TORNEO       */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {step === 1 && (
        <form onSubmit={handleNext} className="bg-[#0e101d] rounded-2xl p-6 sm:p-8 border border-slate-800 space-y-6">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Gamepad2 className="text-purple-400" size={18} />
              ¿Qué juego vas a organizar?
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
              {/* MLBB */}
              <div
                onClick={() => setJuegoCodigo('mlbb')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  juegoCodigo === 'mlbb'
                    ? 'bg-purple-950/50 border-purple-500 shadow-lg shadow-purple-500/20 ring-1 ring-purple-500'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xl">⚔️</span>
                  {juegoCodigo === 'mlbb' && <CheckCircle2 size={18} className="text-purple-400" />}
                </div>
                <p className="font-bold text-white text-sm">Mobile Legends: BB</p>
                <p className="text-[11px] text-slate-400 mt-1">5v5 MOBA • 5 titulares + 2 suplentes</p>
              </div>

              {/* Free Fire */}
              <div
                onClick={() => setJuegoCodigo('free_fire')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  juegoCodigo === 'free_fire'
                    ? 'bg-amber-950/50 border-amber-500 shadow-lg shadow-amber-500/20 ring-1 ring-amber-500'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xl">🔥</span>
                  {juegoCodigo === 'free_fire' && <CheckCircle2 size={18} className="text-amber-400" />}
                </div>
                <p className="font-bold text-white text-sm">Free Fire</p>
                <p className="text-[11px] text-slate-400 mt-1">Battle Royale • 4 titulares + 1 suplente</p>
              </div>

              {/* CODM */}
              <div
                onClick={() => setJuegoCodigo('codm')}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  juegoCodigo === 'codm'
                    ? 'bg-cyan-950/50 border-cyan-500 shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-500'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xl">🎯</span>
                  {juegoCodigo === 'codm' && <CheckCircle2 size={18} className="text-cyan-400" />}
                </div>
                <p className="font-bold text-white text-sm">Call of Duty Mobile</p>
                <p className="text-[11px] text-slate-400 mt-1">5v5 Multijugador • ByD / Dominio</p>
              </div>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-slate-800">
            <div>
              <label className="block text-xs font-bold text-slate-200 mb-1.5">Nombre del Torneo *</label>
              <input
                type="text"
                required
                placeholder="Ej. Copa Latam Mobile Legends 2026"
                value={nombreTorneo}
                onChange={(e) => setNombreTorneo(e.target.value)}
                className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-white font-bold text-sm focus:border-purple-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-200 mb-1.5">Descripción o Reglamento Breve (Opcional)</label>
              <textarea
                rows={3}
                placeholder="Información para los capitanes sobre horarios, servidor y canal de Discord..."
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:border-purple-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-800">
            <button
              type="submit"
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-600/30 transition-all"
            >
              <span>Continuar a Fases y Equipos</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </form>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* PASO 2: CONSTRUCTOR MULTI-FASE CON PLANTILLAS 8,16,32,64,128 */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {step === 2 && (
        <div className="space-y-6">
          
          {/* SECCIÓN 1: BOTONES DE PLANTILLAS RÁPIDAS (8, 16, 32, 64, 128, 40) */}
          <div className="bg-[#0e101d] rounded-2xl p-5 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                <Zap size={14} className="text-amber-400" /> Plantillas Rápidas con 1 Clic:
              </span>
              <span className="text-[11px] text-slate-400">Selecciona para autocompletar las etapas:</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
              
              {/* 8 Equipos */}
              <button
                type="button"
                onClick={() => aplicarPlantilla('8')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  plantillaActiva === '8'
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className="text-lg font-black text-white block">8 Equipos</span>
                <span className="text-[10px] text-slate-400 font-mono">3 Rondas</span>
              </button>

              {/* 16 Equipos */}
              <button
                type="button"
                onClick={() => aplicarPlantilla('16')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  plantillaActiva === '16'
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className="text-lg font-black text-white block">16 Equipos</span>
                <span className="text-[10px] text-slate-400 font-mono">4 Rondas</span>
              </button>

              {/* 32 Equipos */}
              <button
                type="button"
                onClick={() => aplicarPlantilla('32')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  plantillaActiva === '32'
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className="text-lg font-black text-white block">32 Equipos</span>
                <span className="text-[10px] text-slate-400 font-mono">5 Rondas</span>
              </button>

              {/* 64 Equipos */}
              <button
                type="button"
                onClick={() => aplicarPlantilla('64')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  plantillaActiva === '64'
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className="text-lg font-black text-white block">64 Equipos</span>
                <span className="text-[10px] text-slate-400 font-mono">6 Rondas</span>
              </button>

              {/* 128 Equipos */}
              <button
                type="button"
                onClick={() => aplicarPlantilla('128')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  plantillaActiva === '128'
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className="text-lg font-black text-white block">128 Equipos</span>
                <span className="text-[10px] text-cyan-400 font-mono">7 Rondas</span>
              </button>

              {/* 40 Equipos (8 grupos de 5) */}
              <button
                type="button"
                onClick={() => aplicarPlantilla('40_grupos')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  plantillaActiva === '40_grupos'
                    ? 'bg-purple-950/60 border-purple-500 ring-2 ring-purple-500/50 shadow-lg shadow-purple-500/20'
                    : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span className="text-lg font-black text-white block">40 Equipos</span>
                <span className="text-[10px] text-purple-300 font-mono">8 grupos de 5</span>
              </button>

            </div>
          </div>

          {/* SECCIÓN 2: DIAGRAMA VISUAL EN VIVO (PIPELINE DE FASES) */}
          <div className="bg-gradient-to-br from-[#121426] to-[#0e101d] rounded-2xl p-6 border border-purple-500/30 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-extrabold uppercase tracking-widest text-slate-300 flex items-center gap-2">
                <Layers size={14} className="text-cyan-400" />
                Ruta de Clasificación en Vivo ({totalEquipos} Equipos Totales)
              </h3>
              <span className="text-xs text-purple-300 font-mono font-bold">
                {fases.length} {fases.length === 1 ? 'Etapa' : 'Etapas Encadenadas'}
              </span>
            </div>

            <div className="flex flex-col md:flex-row items-center justify-between gap-4 overflow-x-auto py-2">
              {fases.map((f, idx) => (
                <React.Fragment key={f.id}>
                  {/* Card de la Fase */}
                  <div className="w-full md:w-64 bg-[#0a0a14] p-4 rounded-xl border border-slate-800 space-y-2 relative shadow-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        Etapa #{idx + 1}
                      </span>
                      <span className="text-[11px] font-mono text-cyan-400 font-bold">
                        {f.equiposEntran} Equipos
                      </span>
                    </div>

                    <p className="text-xs font-extrabold text-white truncate">{f.nombre}</p>
                    
                    <div className="text-[11px] text-slate-400 font-mono bg-slate-900/80 p-2 rounded-lg border border-slate-800/80">
                      {f.formato === 'round_robin' && (
                        <span>{f.numGrupos} Grupos de {f.equiposPorGrupo || Math.floor(f.equiposEntran / (f.numGrupos || 8))} escuadras</span>
                      )}
                      {f.formato === 'eliminacion_simple' && (
                        <span>Eliminación Directa en Llaves</span>
                      )}
                      {f.formato === 'eliminacion_doble' && (
                        <span>Eliminación Doble (Upper/Lower)</span>
                      )}
                      {f.formato === 'suizo' && (
                        <span>Sistema Suizo (5 rondas de récord)</span>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[11px] pt-1">
                      <span className="text-slate-500">Avanzan:</span>
                      <span className="font-bold text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 size={12} />
                        {f.cuposAvance} {idx === fases.length - 1 ? 'Campeón 🏆' : 'Equipos ➔'}
                      </span>
                    </div>
                  </div>

                  {/* Flecha a la siguiente etapa */}
                  {idx < fases.length - 1 && (
                    <div className="flex items-center justify-center text-purple-400 my-2 md:my-0">
                      <ArrowRight size={20} className="hidden md:block animate-pulse" />
                      <span className="md:hidden text-xs font-bold text-purple-300">↓ Pasan {f.cuposAvance} Equipos ↓</span>
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* SECCIÓN 3: CONFIGURACIÓN DETALLADA DE CADA ETAPA */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Settings2 className="text-cyan-400" size={18} />
                Ajustar o Personalizar cada Etapa
              </h2>

              <button
                type="button"
                onClick={handleAddFase}
                className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-md transition-all"
              >
                <Plus size={14} /> Añadir Siguiente Etapa
              </button>
            </div>

            {/* Fases List Cards */}
            {fases.map((fase, index) => (
              <div key={fase.id} className="bg-[#0e101d] rounded-2xl p-6 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2 flex-1">
                    <span className="w-6 h-6 rounded-lg bg-purple-950 border border-purple-500/40 text-purple-300 font-black text-xs flex items-center justify-center">
                      {index + 1}
                    </span>
                    <input
                      type="text"
                      value={fase.nombre}
                      onChange={(e) => updateFase(index, { nombre: e.target.value })}
                      className="bg-transparent text-white font-bold text-sm focus:outline-none border-b border-transparent focus:border-purple-500 w-full"
                    />
                  </div>

                  {fases.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveFase(index)}
                      className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-950/30 transition-colors ml-2"
                      title="Eliminar esta etapa"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                  {/* Formato */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">Formato de esta Etapa</label>
                    <select
                      value={fase.formato}
                      onChange={(e) => updateFase(index, { formato: e.target.value as any })}
                      className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-white font-semibold focus:border-purple-500 focus:outline-none"
                    >
                      <option value="eliminacion_simple">🏆 Eliminación Simple (Brackets directos)</option>
                      <option value="eliminacion_doble">⚔️ Eliminación Doble (Upper / Lower)</option>
                      <option value="suizo">👑 Sistema Suizo</option>
                      <option value="round_robin">📊 Fase de Grupos (Round Robin)</option>
                    </select>
                  </div>

                  {/* Equipos que entran */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">Equipos en esta Etapa</label>
                    <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-cyan-300 font-mono font-bold">
                      {fase.equiposEntran} Escuadras {index > 0 ? '(Recibidos de la fase anterior)' : ''}
                    </div>
                  </div>

                  {/* Cupos que avanzan */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">
                      {index === fases.length - 1 ? 'Ganador Final' : '¿Cuántos clasifican a la siguiente etapa?'}
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={fase.equiposEntran}
                      value={fase.cuposAvance}
                      onChange={(e) => updateFase(index, { cuposAvance: Number(e.target.value) })}
                      className="w-full p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-emerald-400 font-mono font-bold focus:border-purple-500 focus:outline-none"
                    />
                  </div>

                  {/* Formato de Series (Best-Of) */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 mb-1">Formato de Series (Best-Of)</label>
                    <div className="flex gap-1.5">
                      {([1, 3, 5] as const).map(bo => (
                        <button
                          key={bo}
                          type="button"
                          onClick={() => updateFase(index, { bo })}
                          className={`flex-1 py-2.5 rounded-lg text-xs font-bold border transition-all ${
                            fase.bo === bo
                              ? 'border-cyan-500 bg-cyan-500/20 text-cyan-300'
                              : 'border-slate-800 bg-slate-950 text-slate-500 hover:border-slate-700'
                          }`}
                        >
                          BO{bo}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* BO escalonado por ronda (solo brackets de eliminación) */}
                {(fase.formato === 'eliminacion_simple' || fase.formato === 'eliminacion_doble') && (() => {
                  const rondasTotales = totalRondas(fase.formato, fase.equiposEntran);
                  return (
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-300">
                        Escalar el Best-Of por ronda (opcional) — cualquier cantidad de tramos
                      </span>
                      <button
                        type="button"
                        onClick={() => {
                          const tramos = fase.tramosBo || [];
                          const ultimo = tramos[tramos.length - 1];
                          const siguienteRonda = Math.min(ultimo ? ultimo.ronda + 1 : 2, rondasTotales);
                          updateFase(index, { tramosBo: [...tramos, { ronda: siguienteRonda, bo: 3 }] });
                        }}
                        disabled={(fase.tramosBo?.length ?? 0) >= rondasTotales}
                        className="flex items-center gap-1 px-2.5 py-1.5 bg-purple-600/20 hover:bg-purple-600/40 border border-purple-500/30 text-purple-300 text-[11px] font-semibold rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Plus size={12} /> Agregar tramo
                      </button>
                    </div>

                    {(!fase.tramosBo || fase.tramosBo.length === 0) && (
                      <p className="text-slate-500">Todas las rondas se juegan a BO{fase.bo}.</p>
                    )}

                    {fase.tramosBo && fase.tramosBo.length > 0 && (
                      <div className="space-y-2">
                        {fase.tramosBo.map((tramo, tIdx) => (
                          <div key={tIdx} className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg p-2.5">
                            <span className="text-slate-500 whitespace-nowrap">Desde ronda</span>
                            <input
                              type="number" min={1} max={rondasTotales} value={tramo.ronda}
                              onChange={(e) => {
                                const valor = Math.min(Math.max(parseInt(e.target.value) || 1, 1), rondasTotales);
                                const tramos = [...(fase.tramosBo || [])];
                                tramos[tIdx] = { ...tramos[tIdx], ronda: valor };
                                updateFase(index, { tramosBo: tramos });
                              }}
                              className="w-16 bg-slate-950 border border-slate-800 text-white rounded-lg px-2 py-1.5 text-center font-mono font-bold"
                            />
                            <span className="text-slate-500">→</span>
                            <div className="flex gap-1.5 flex-1">
                              {([1, 3, 5] as const).map(bo => (
                                <button
                                  key={bo}
                                  type="button"
                                  onClick={() => {
                                    const tramos = [...(fase.tramosBo || [])];
                                    tramos[tIdx] = { ...tramos[tIdx], bo };
                                    updateFase(index, { tramosBo: tramos });
                                  }}
                                  className={`flex-1 py-1.5 rounded-lg font-bold border transition-all ${
                                    tramo.bo === bo
                                      ? 'border-cyan-500 bg-cyan-500/20 text-cyan-300'
                                      : 'border-slate-800 bg-slate-950 text-slate-500 hover:border-slate-700'
                                  }`}
                                >
                                  BO{bo}
                                </button>
                              ))}
                            </div>
                            <button
                              type="button"
                              onClick={() => updateFase(index, { tramosBo: (fase.tramosBo || []).filter((_, i) => i !== tIdx) })}
                              className="text-slate-600 hover:text-rose-400 p-1"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ))}
                        <p className="text-[10px] text-slate-500">
                          {fase.formato === 'eliminacion_doble'
                            ? `Esta llave doble de ${fase.equiposEntran} equipos tiene ${rondasTotales} rondas en total (ronda 1 = primera de la llave alta; la gran final es la ronda ${rondasTotales}, contando las rondas de la llave baja intercaladas).`
                            : `Este cuadro de ${fase.equiposEntran} equipos tiene ${rondasTotales} rondas en total (ronda ${rondasTotales} = final).`}
                        </p>
                      </div>
                    )}
                  </div>
                  );
                })()}

                {/* Si es grupos, sub-opciones */}
                {fase.formato === 'round_robin' && (
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1 font-semibold">Cantidad de Grupos</label>
                      <input
                        type="number"
                        min={2}
                        max={16}
                        value={fase.numGrupos || 8}
                        onChange={(e) => updateFase(index, { numGrupos: Number(e.target.value) })}
                        className="w-full p-2 rounded-lg bg-slate-900 border border-slate-800 text-white font-mono font-bold"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1 font-semibold">Equipos por Grupo</label>
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-purple-300 font-mono font-bold">
                        {Math.floor(fase.equiposEntran / (fase.numGrupos || 8))} Equipos / grupo
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1 font-semibold">Clasifican por Grupo (Top X)</label>
                      <input
                        type="number"
                        min={1}
                        max={4}
                        value={fase.clasificadosPorGrupo || 2}
                        onChange={(e) => updateFase(index, { clasificadosPorGrupo: Number(e.target.value) })}
                        className="w-full p-2 rounded-lg bg-slate-900 border border-slate-800 text-emerald-400 font-mono font-bold"
                      />
                    </div>
                  </div>
                )}

                {/* Advertencia: equipos no potencia de 2 para brackets */}
                {(fase.formato === 'eliminacion_simple' || fase.formato === 'eliminacion_doble') &&
                  fase.equiposEntran > 1 &&
                  (fase.equiposEntran & (fase.equiposEntran - 1)) !== 0 && (
                  <div className="flex items-center gap-2 p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-500/40 text-[11px] text-cyan-300">
                    <span className="text-cyan-400">✨</span>
                    <span>
                      <span>
                        <strong>{fase.equiposEntran} equipos</strong> no es potencia de 2.
                        El sistema completará automáticamente con <strong className="text-cyan-300">{Math.pow(2, Math.ceil(Math.log2(fase.equiposEntran))) - fase.equiposEntran} BYE{Math.pow(2, Math.ceil(Math.log2(fase.equiposEntran))) - fase.equiposEntran !== 1 ? 's' : ''}</strong> hasta {Math.pow(2, Math.ceil(Math.log2(fase.equiposEntran)))} slots.
                        Los top seeds recibirán pase directo (BYE) a la Ronda 2.
                      </span>
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center gap-2"
            >
              <ArrowLeft size={14} /> Volver al Paso 1
            </button>

            <button
              type="button"
              onClick={() => setStep(3)}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-purple-600/30 transition-all"
            >
              <span>Continuar al Paso 3 (Premios y Publicar)</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* PASO 3: FECHAS, PREMIOS Y PUBLICACIÓN                    */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {step === 3 && (
        <form onSubmit={handleCrearTorneo} className="bg-[#0e101d] rounded-2xl p-6 sm:p-8 border border-slate-800 space-y-6">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Calendar className="text-amber-400" size={18} />
              Fechas y Bolsa de Premios
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Configura la fecha de inicio y la recompensa del torneo.</p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Fecha de Inicio</label>
                <input
                  type="date"
                  value={fechaInicio}
                  onChange={(e) => setFechaInicio(e.target.value)}
                  className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-white font-bold focus:border-purple-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">Bolsa de Premios (Prize Pool)</label>
                <input
                  type="text"
                  placeholder="Ej: $1,500 USD o 5,000 Diamantes"
                  value={bolsaPremios}
                  onChange={(e) => setBolsaPremios(e.target.value)}
                  className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-amber-300 font-bold focus:border-purple-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Resumen Final de la Estructura */}
          <div className="p-5 rounded-xl bg-gradient-to-br from-purple-950/40 to-slate-950 border border-purple-500/30 space-y-3">
            <h3 className="font-bold text-sm text-white flex items-center gap-2">
              <CheckCircle2 size={16} className="text-purple-400" />
              Resumen Final del Torneo
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Torneo</span>
                <p className="font-bold text-white truncate">{nombreTorneo}</p>
              </div>

              <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Participantes</span>
                <p className="font-bold text-cyan-300 font-mono">{totalEquipos} Equipos</p>
              </div>

              <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Etapas</span>
                <p className="font-bold text-purple-300">{fases.length} Fases Encadenadas</p>
              </div>

              <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800">
                <span className="text-[10px] text-slate-500 uppercase block">Premios</span>
                <p className="font-bold text-amber-300 font-mono">{bolsaPremios}</p>
              </div>
            </div>

            <div className="mt-2 p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-300 space-y-1">
              <p className="font-bold text-purple-400 uppercase text-[10px]">Ruta de Clasificación Encadenada:</p>
              {fases.map((f, i) => (
                <p key={f.id} className="flex items-center gap-2">
                  <span className="text-slate-500 font-mono">Paso {i + 1}:</span>
                  <strong className="text-white">{f.nombre}</strong>
                  <span className="text-slate-400">({f.equiposEntran} equipos ➔ clasifican {f.cuposAvance})</span>
                </p>
              ))}
            </div>
          </div>

          {errorSubmit && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle size={15} /> <span>{errorSubmit}</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold flex items-center gap-2"
            >
              <ArrowLeft size={14} /> Volver a Fases
            </button>

            <button
              type="submit"
              disabled={isSubmitting || creadoExitoso}
              className={`px-8 py-3.5 rounded-xl text-white font-extrabold text-sm flex items-center gap-2 shadow-xl transition-all cursor-pointer ${
                creadoExitoso
                  ? 'bg-emerald-600 shadow-emerald-600/30'
                  : isSubmitting
                  ? 'bg-purple-700 opacity-90'
                  : 'bg-gradient-to-r from-emerald-600 via-purple-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 shadow-purple-600/30'
              }`}
            >
              <Sparkles size={16} />
              <span>{creadoExitoso ? '✓ ¡Torneo Creado! Redirigiendo...' : isSubmitting ? 'Guardando Torneo...' : '🚀 ¡Crear y Publicar Torneo!'}</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
