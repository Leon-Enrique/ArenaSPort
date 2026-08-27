'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Swords, CheckCircle2, Clock, ShieldAlert,
  Play, Trophy, Edit3, Check, X, Filter, Loader2, AlertCircle, LogIn, TimerOff, Gavel, CalendarClock
} from 'lucide-react';
import { api, ApiError, mapFase, mapPartida } from '@/lib/api';
import { ApiEdicion, ApiFase, ApiPartida, ApiTorneo } from '@/lib/api-types';
import GroupStageView from '@/components/torneos/GroupStageView';
import SwissBracketView from '@/components/torneos/SwissBracketView';
import BracketView from '@/components/torneos/BracketView';
import DoubleEliminationView from '@/components/torneos/DoubleEliminationView';

export default function FasePartidasAdminPage() {
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;
  const faseId = params.faseId as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [fase, setFase] = useState<ApiFase | null>(null);
  const [partidas, setPartidas] = useState<ApiPartida[]>([]);
  const [tabla, setTabla] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedRonda, setSelectedRonda] = useState<number | 'todas'>('todas');
  const [editingPartidaId, setEditingPartidaId] = useState<number | null>(null);
  const [scoreTeamA, setScoreTeamA] = useState(0);
  const [scoreTeamB, setScoreTeamB] = useState(0);
  const [guardando, setGuardando] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [abriendoCheckin, setAbriendoCheckin] = useState<number | null>(null);
  const [resolviendoCheckin, setResolviendoCheckin] = useState<number | null>(null);
  const [resolviendoReporte, setResolviendoReporte] = useState<number | null>(null);
  const [programandoPartidaId, setProgramandoPartidaId] = useState<number | null>(null);
  const [horarioValor, setHorarioValor] = useState('');
  const [guardandoHorario, setGuardandoHorario] = useState(false);
  const [programandoRonda, setProgramandoRonda] = useState(false);
  const [horarioRondaValor, setHorarioRondaValor] = useState('');
  const [guardandoRonda, setGuardandoRonda] = useState(false);
  const cardRefs = React.useRef<Map<number, HTMLDivElement>>(new Map());

  const showToast = (msg: string) => {
    setSuccessToast(msg);
    setTimeout(() => setSuccessToast(null), 3000);
  };

  const cargar = async () => {
    setLoading(true);
    try {
      const [t, ed, fs] = await Promise.all([
        api.getTorneoById(torneoId), api.getEdicionById(edId), api.getFasesByEdicion(edId),
      ]);
      setTorneo(t);
      setEdicion(ed);
      const f = fs.find(x => String(x.id) === faseId) || null;
      setFase(f);
      if (f?.modelo_competencia === 'multi_equipo') {
        const tb = await api.getTablaFase(edId, faseId).catch(() => []);
        setTabla(tb);
      } else {
        const ps = await api.getPartidasByFase(faseId).catch(() => []);
        setPartidas(ps);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, [torneoId, edId, faseId]);

  const isMultiEquipo = fase?.modelo_competencia === 'multi_equipo';
  const esFaseSuiza = fase?.formato === 'suizo';
  const esFaseEliminacionSimple = fase?.formato === 'eliminacion_simple';
  const esFaseEliminacionDoble = fase?.formato === 'eliminacion_doble';

  const handleSelectFromBracket = (partidaId: string) => {
    const raw = partidas.find(p => String(p.id) === partidaId);
    if (!raw) return;
    const eqA = raw.participaciones?.[0];
    const eqB = raw.participaciones?.[1];
    if (!eqB) return;
    setEditingPartidaId(raw.id);
    setScoreTeamA(eqA?.mapas_ganados ?? 0);
    setScoreTeamB(eqB?.mapas_ganados ?? 0);
    cardRefs.current.get(raw.id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleSaveScore = async (partida: ApiPartida) => {
    const eqA = partida.participaciones[0];
    const eqB = partida.participaciones[1];
    if (!eqA || !eqB) return;
    setGuardando(true);
    setError(null);
    try {
      if (partida.estado === 'confirmada') {
        await api.corregirResultado(faseId, String(partida.id), {
          resultados: [
            { equipo_id: eqA.equipo.id, mapas_ganados: scoreTeamA },
            { equipo_id: eqB.equipo.id, mapas_ganados: scoreTeamB },
          ],
          motivo: 'Corrección manual del organizador desde el panel de admin.',
        });
      } else {
        await api.reportarResultado(faseId, String(partida.id), {
          equipo_id: eqA.equipo.id, marcador_propio: scoreTeamA, marcador_rival: scoreTeamB,
        });
        await api.confirmarResultadoAdmin(faseId, String(partida.id), String(eqB.equipo.id));
      }
      showToast('Marcador guardado y confirmado.');
      setEditingPartidaId(null);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el marcador.');
    } finally {
      setGuardando(false);
    }
  };

  const handleAbrirCheckin = async (partidaId: number) => {
    setError(null);
    setAbriendoCheckin(partidaId);
    try {
      await api.abrirCheckinPartida(faseId, String(partidaId), 15);
      showToast('Check-in abierto — los capitanes tienen 15 minutos para confirmar presencia.');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo abrir el check-in.');
    } finally {
      setAbriendoCheckin(null);
    }
  };

  const handleResolverCheckin = async (partidaId: number) => {
    setError(null);
    setResolviendoCheckin(partidaId);
    try {
      await api.resolverCheckinPartida(faseId, String(partidaId));
      showToast('Check-in resuelto.');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo resolver el check-in.');
    } finally {
      setResolviendoCheckin(null);
    }
  };

  const handleResolverReporteVencido = async (partidaId: number) => {
    setError(null);
    setResolviendoReporte(partidaId);
    try {
      await api.resolverReporteVencido(faseId, String(partidaId));
      showToast('Reporte auto-confirmado por vencimiento de plazo.');
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo resolver el reporte vencido.');
    } finally {
      setResolviendoReporte(null);
    }
  };

  const handleGuardarHorario = async (partidaId: number) => {
    if (!horarioValor) return;
    setError(null);
    setGuardandoHorario(true);
    try {
      await api.programarPartida(faseId, String(partidaId), new Date(horarioValor).toISOString());
      showToast('Horario guardado — el check-in se va a abrir solo 15 minutos antes.');
      setProgramandoPartidaId(null);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar el horario.');
    } finally {
      setGuardandoHorario(false);
    }
  };

  const handleGuardarHorarioRonda = async () => {
    if (!horarioRondaValor || selectedRonda === 'todas') return;
    const objetivo = partidas.filter(p => p.ronda === selectedRonda && p.estado === 'programada');
    if (objetivo.length === 0) {
      setError('No hay partidas "programada" en esta ronda para programar.');
      return;
    }
    setError(null);
    setGuardandoRonda(true);
    try {
      const isoValor = new Date(horarioRondaValor).toISOString();
      const resultados = await Promise.allSettled(
        objetivo.map(p => api.programarPartida(faseId, String(p.id), isoValor))
      );
      const fallos = resultados.filter(r => r.status === 'rejected').length;
      if (fallos > 0) {
        setError(`Se programaron ${objetivo.length - fallos} de ${objetivo.length} partidas — ${fallos} fallaron.`);
      } else {
        showToast(`Ronda ${selectedRonda} programada: ${objetivo.length} partida(s). El check-in se abre solo 15 minutos antes.`);
      }
      setProgramandoRonda(false);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo programar la ronda.');
    } finally {
      setGuardandoRonda(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando partidas...
      </div>
    );
  }

  const rondas = Array.from(new Set(partidas.map(p => p.ronda).filter((r): r is number => r != null))).sort((a, b) => a - b);
  const filteredPartidas = selectedRonda === 'todas' ? partidas : partidas.filter(p => p.ronda === selectedRonda);

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-6">
      {successToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/90 text-white px-5 py-3 rounded-[6px] shadow-xl backdrop-blur-md flex items-center gap-2 text-sm font-semibold">
          <CheckCircle2 size={18} /> {successToast}
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-tinta-4">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">{torneo?.nombre}</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases`} className="hover:text-white transition-colors">Fases</Link>
        <span>/</span>
        <span className="text-tinta-2">{fase?.nombre}</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs text-tinta-3">{edicion?.nombre}</span>
          <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
            <Swords className="text-acento-claro" /> {fase?.nombre} - Administrador de Partidas
          </h1>
        </div>
        <Link
          href={`/admin/torneos/${torneoId}/ediciones/${edId}/fases/${faseId}/tabla`}
          className="flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 border border-borde text-white text-xs font-semibold rounded-[6px] transition-all w-fit"
        >
          <Trophy size={14} className="text-atencion" /> Ver Tabla de Posiciones
        </Link>
      </div>

      {error && (
        <div className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
          <AlertCircle size={15} /> <span>{error}</span>
        </div>
      )}

      {isMultiEquipo ? (
        <div className="bg-superficie border border-borde rounded-[6px] p-6 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-white">Tabla de Posiciones (Multi-Equipo)</h2>
            <p className="text-xs text-tinta-3">La carga de resultados por caída para formatos battle royale todavía no está disponible desde este panel — usá el endpoint de la API directamente por ahora.</p>
          </div>
          <GroupStageView grupos={tabla} />
        </div>
      ) : partidas.length === 0 ? (
        <div className="bg-superficie border border-borde rounded-[6px] p-12 text-center text-tinta-4">
          <Swords size={36} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Esta fase todavía no tiene partidas — sorteala desde la lista de fases.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {esFaseSuiza && (
            <SwissBracketView
              partidas={partidas.map(p => mapPartida(p, fase?.nombre))}
              metaVictorias={fase?.config?.meta_victorias}
              metaDerrotas={fase?.config?.meta_derrotas}
              onSelectPartida={(p) => handleSelectFromBracket(p.id)}
            />
          )}

          {esFaseEliminacionSimple && fase && (
            <BracketView
              fases={[mapFase(fase, partidas.map(p => mapPartida(p, fase.nombre)))]}
              onSelectPartida={(p) => handleSelectFromBracket(p.id)}
            />
          )}

          {esFaseEliminacionDoble && (
            <DoubleEliminationView
              partidas={partidas.map(p => mapPartida(p, fase?.nombre))}
              onSelectPartida={(p) => handleSelectFromBracket(p.id)}
            />
          )}

          <div className="flex items-center justify-between gap-4 bg-superficie border border-borde rounded-[6px] p-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter size={15} className="text-acento-claro" />
              <span className="text-xs font-semibold text-tinta-2">Filtrar por Ronda:</span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setSelectedRonda('todas')}
                  className={`px-3 py-1 rounded-[4px] text-xs font-medium transition-all ${selectedRonda === 'todas' ? 'bg-acento text-white font-bold' : 'bg-white/5 text-tinta-3 hover:text-white'}`}
                >
                  Todas ({partidas.length})
                </button>
                {rondas.map(r => (
                  <button
                    key={r}
                    onClick={() => setSelectedRonda(r)}
                    className={`px-3 py-1 rounded-[4px] text-xs font-medium transition-all ${selectedRonda === r ? 'bg-acento text-white font-bold' : 'bg-white/5 text-tinta-3 hover:text-white'}`}
                  >
                    Ronda {r}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {selectedRonda !== 'todas' && (
                programandoRonda ? (
                  <div className="flex items-center gap-2 flex-wrap">
                    <input
                      type="datetime-local"
                      value={horarioRondaValor}
                      onChange={(e) => setHorarioRondaValor(e.target.value)}
                      className="bg-fondo border border-acento rounded-[4px] px-2 py-1.5 text-xs text-white"
                    />
                    <button
                      onClick={() => setProgramandoRonda(false)}
                      className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 text-tinta-2 rounded-[4px] text-xs font-semibold"
                    >
                      <X size={12} />
                    </button>
                    <button
                      onClick={handleGuardarHorarioRonda}
                      disabled={guardandoRonda || !horarioRondaValor}
                      className="px-3 py-1.5 bg-acento hover:bg-acento text-white rounded-[4px] text-xs font-bold flex items-center gap-1 disabled:opacity-50"
                    >
                      {guardandoRonda ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />} Guardar
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => { setProgramandoRonda(true); setHorarioRondaValor(''); }}
                    title="Aplica el mismo horario a todas las partidas 'programada' de esta ronda de una sola vez."
                    className="px-3 py-1.5 bg-acento/20 hover:bg-acento/40 border border-borde text-acento-claro rounded-[4px] text-xs font-semibold flex items-center gap-1 transition-all"
                  >
                    <CalendarClock size={12} /> Programar Ronda {selectedRonda}
                  </button>
                )
              )}
              <div className="text-xs text-tinta-3">
                Formato: <span className="text-tinta-2 font-semibold uppercase">{fase?.formato.replace('_', ' ')}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredPartidas.map((partida) => {
              const eqA = partida.participaciones?.[0];
              const eqB = partida.participaciones?.[1];
              const isEditing = editingPartidaId === partida.id;
              const isConfirmed = partida.estado === 'confirmada';
              const isDispute = partida.estado === 'en_disputa';
              const isBye = partida.estado === 'bye';

              return (
                <div
                  key={partida.id}
                  ref={(el) => { if (el) cardRefs.current.set(partida.id, el); else cardRefs.current.delete(partida.id); }}
                  className={`bg-superficie border rounded-[6px] p-5 transition-all relative group ${
                    isDispute ? 'border-red-500/40' : editingPartidaId === partida.id ? 'border-acento/60 ring-1 ring-violet-500/40' : 'border-borde hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-4 pb-3 border-b border-borde-sutil">
                    <span className="px-2 py-0.5 rounded-md bg-white/5 font-mono text-[11px] text-tinta-3">Ronda {partida.ronda ?? '—'}</span>
                    <div>
                      {isConfirmed && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-ok bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                          <CheckCircle2 size={11} /> Confirmada
                        </span>
                      )}
                      {isDispute && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-vivo bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">
                          <ShieldAlert size={11} /> Disputa Abierta
                        </span>
                      )}
                      {isBye && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-tinta-2 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">BYE</span>
                      )}
                      {partida.estado === 'programada' && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-tinta-3 bg-white/5 px-2 py-0.5 rounded-full border border-borde">
                          <Clock size={11} />
                          {partida.programada_para
                            ? `Check-in auto a las ${new Date(new Date(partida.programada_para).getTime() - 15 * 60000).toLocaleString('es', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}`
                            : 'Programada'}
                        </span>
                      )}
                      {partida.estado === 'check_in' && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-atencion bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                          <LogIn size={11} /> Check-in abierto
                          {partida.checkin_cierra_at && ` · cierra ${new Date(partida.checkin_cierra_at).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}`}
                        </span>
                      )}
                      {partida.estado === 'en_curso' && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-tinta-2 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">
                          <Play size={11} /> En curso
                        </span>
                      )}
                      {partida.estado === 'reportada' && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-fuchsia-300 bg-fuchsia-500/10 px-2 py-0.5 rounded-full border border-fuchsia-500/20">
                          <Clock size={11} /> Esperando confirmación del rival
                        </span>
                      )}
                    </div>
                  </div>

                  {!eqB ? (
                    <div className="p-3 text-xs text-tinta-3 text-center">Falta el rival — se completa cuando avance la ronda anterior.</div>
                  ) : (
                    <>
                      <div className="space-y-2.5 mb-4">
                        {[eqA, eqB].map((p, idx) => (
                          <div
                            key={idx}
                            className={`flex items-center justify-between p-3 rounded-[6px] transition-all ${p?.es_ganador ? 'bg-green-500/10 border border-green-500/30' : 'bg-white/[0.02] border border-borde-sutil'}`}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`w-8 h-8 rounded-[4px] ${idx === 0 ? 'bg-acento/30 border-borde' : 'bg-cyan-600/30 border-cyan-500/30'} border flex items-center justify-center font-bold text-xs text-white`}>
                                {(p?.equipo.tag || p?.equipo.nombre || '??').slice(0, 3)}
                              </div>
                              <p className={`text-sm font-bold leading-tight ${p?.es_ganador ? 'text-green-300' : 'text-white'}`}>{p?.equipo.nombre}</p>
                            </div>
                            {isEditing ? (
                              <input
                                type="number" min={0} max={5}
                                value={idx === 0 ? scoreTeamA : scoreTeamB}
                                onChange={(e) => idx === 0 ? setScoreTeamA(Number(e.target.value)) : setScoreTeamB(Number(e.target.value))}
                                className="w-12 bg-fondo border border-acento rounded-[4px] text-center font-mono font-bold text-white text-base py-1"
                              />
                            ) : (
                              <span className={`text-xl font-black font-mono px-2.5 py-0.5 rounded-[4px] ${p?.es_ganador ? 'text-ok bg-green-500/20' : 'text-tinta-2 bg-white/5'}`}>
                                {p?.mapas_ganados ?? 0}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>

                      {partida.estado === 'programada' && !isEditing && (
                        programandoPartidaId === partida.id ? (
                          <div className="flex items-center justify-end gap-2 pb-2 flex-wrap">
                            <input
                              type="datetime-local"
                              value={horarioValor}
                              onChange={(e) => setHorarioValor(e.target.value)}
                              className="bg-fondo border border-acento rounded-[4px] px-2 py-1.5 text-xs text-white"
                            />
                            <button
                              onClick={() => setProgramandoPartidaId(null)}
                              className="px-2.5 py-1.5 bg-white/5 hover:bg-white/10 text-tinta-2 rounded-[4px] text-xs font-semibold"
                            >
                              <X size={12} />
                            </button>
                            <button
                              onClick={() => handleGuardarHorario(partida.id)}
                              disabled={guardandoHorario || !horarioValor}
                              className="px-3 py-1.5 bg-acento hover:bg-acento text-white rounded-[4px] text-xs font-bold flex items-center gap-1 disabled:opacity-50"
                            >
                              {guardandoHorario ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />} Guardar
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-2 pb-2">
                            <button
                              onClick={() => { setProgramandoPartidaId(partida.id); setHorarioValor(''); }}
                              title="El check-in se va a abrir solo 15 minutos antes de este horario."
                              className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-borde text-tinta-2 hover:text-white rounded-[4px] text-xs font-semibold flex items-center gap-1 transition-all"
                            >
                              <CalendarClock size={12} /> {partida.programada_para ? 'Reprogramar' : 'Programar Horario'}
                            </button>
                            <button
                              onClick={() => handleAbrirCheckin(partida.id)}
                              disabled={abriendoCheckin === partida.id}
                              title="Abre el check-in ahora mismo (15 min), sin esperar el horario programado."
                              className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/40 border border-amber-500/30 text-atencion rounded-[4px] text-xs font-semibold flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              {abriendoCheckin === partida.id ? <Loader2 size={12} className="animate-spin" /> : <LogIn size={12} />} Abrir Ya
                            </button>
                          </div>
                        )
                      )}

                      {(partida.estado === 'check_in' || partida.estado === 'reportada') && !isEditing && (
                        <div className="flex items-center justify-end gap-2 pb-2">
                          {partida.estado === 'check_in' && (
                            <button
                              onClick={() => handleResolverCheckin(partida.id)}
                              disabled={resolviendoCheckin === partida.id || (!!partida.checkin_cierra_at && new Date(partida.checkin_cierra_at) > new Date())}
                              title="Cierra la ventana de check-in vencida — aplica walkover si algún equipo no confirmó."
                              className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/40 border border-amber-500/30 text-atencion rounded-[4px] text-xs font-semibold flex items-center gap-1 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              {resolviendoCheckin === partida.id ? <Loader2 size={12} className="animate-spin" /> : <TimerOff size={12} />} Resolver Check-in
                            </button>
                          )}
                          {partida.estado === 'reportada' && (
                            <button
                              onClick={() => handleResolverReporteVencido(partida.id)}
                              disabled={resolviendoReporte === partida.id}
                              title="Ya se resuelve solo al vencer el plazo (si tiene evidencia) con solo recargar esta página — este botón es para forzarlo ahora mismo."
                              className="px-3 py-1.5 bg-fuchsia-600/20 hover:bg-fuchsia-600/40 border border-fuchsia-500/30 text-fuchsia-300 rounded-[4px] text-xs font-semibold flex items-center gap-1 transition-all disabled:opacity-50"
                            >
                              {resolviendoReporte === partida.id ? <Loader2 size={12} className="animate-spin" /> : <Gavel size={12} />} Forzar Resolución
                            </button>
                          )}
                        </div>
                      )}

                      <div className="flex items-center justify-end gap-2 pt-2">
                        {isEditing ? (
                          <>
                            <button
                              onClick={() => setEditingPartidaId(null)}
                              className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-tinta-2 hover:text-white rounded-[4px] text-xs font-semibold flex items-center gap-1"
                            >
                              <X size={12} /> Cancelar
                            </button>
                            <button
                              onClick={() => handleSaveScore(partida)}
                              disabled={guardando}
                              className="px-3.5 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-[4px] text-xs font-bold flex items-center gap-1 shadow-md shadow-green-600/20 disabled:opacity-50"
                            >
                              {guardando ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />} Guardar Resultado
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingPartidaId(partida.id);
                              setScoreTeamA(eqA?.mapas_ganados ?? 0);
                              setScoreTeamB(eqB?.mapas_ganados ?? 0);
                            }}
                            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-tinta-2 hover:text-white rounded-[4px] text-xs font-semibold flex items-center gap-1 transition-all"
                          >
                            <Edit3 size={12} /> Editar Score
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
