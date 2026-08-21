'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import BracketView from '@/components/torneos/BracketView';
import GroupStageView from '@/components/torneos/GroupStageView';
import DoubleEliminationView from '@/components/torneos/DoubleEliminationView';
import SwissBracketView from '@/components/torneos/SwissBracketView';
import TeamsList from '@/components/torneos/TeamsList';
import PartidaDetailModal from '@/components/torneos/PartidaDetailModal';
import { api, mapFase, mapPartida, mapResumenAEdicion } from '@/lib/api';
import { ApiFase, ApiResumenEdicion, ApiTablaGrupo } from '@/lib/api-types';
import { Partida } from '@/types';
import {
  Trophy, Shield, Users, Calendar, Award, FileText,
  Sword, Layers, Loader2,
} from 'lucide-react';

const ESTADO_LABEL: Record<string, string> = {
  borrador: 'Borrador',
  inscripciones_abiertas: 'Inscripciones Abiertas',
  inscripciones_cerradas: 'Inscripciones Cerradas',
  en_curso: 'En Curso',
  finalizada: 'Finalizado',
  cancelada: 'Cancelado',
};

const FORMATO_LABEL: Record<string, string> = {
  eliminacion_simple: 'Eliminación Simple',
  eliminacion_doble: 'Doble Eliminación',
  round_robin: 'Fase de Grupos (Round Robin)',
  suizo: 'Sistema Suizo',
  liga_acumulativa: 'Liga Acumulativa',
};

export default function TorneoDetailClient({ resumenInicial }: { resumenInicial: ApiResumenEdicion }) {
  const edicion = mapResumenAEdicion(resumenInicial);
  const fases = resumenInicial.fases;

  const [activeTab, setActiveTab] = useState<'brackets' | 'teams' | 'overview'>('brackets');
  const [activeFaseId, setActiveFaseId] = useState<number | null>(fases[0]?.id ?? null);
  const [selectedPartida, setSelectedPartida] = useState<Partida | null>(null);

  const activeFase = fases.find(f => f.id === activeFaseId) || fases[0];

  const [partidas, setPartidas] = useState<Partida[]>([]);
  const [tabla, setTabla] = useState<ApiTablaGrupo[]>([]);
  const [loadingFaseData, setLoadingFaseData] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [vistaSuizo, setVistaSuizo] = useState<'cruces' | 'tabla'>('cruces');

  const esFaseSuiza = activeFase?.formato === 'suizo';
  const esFaseDeTabla = activeFase?.formato === 'round_robin' || esFaseSuiza;

  useEffect(() => {
    if (!activeFase) return;
    let activo = true;
    setLoadingFaseData(true);

    const pedidos: Promise<any>[] = [];
    if (esFaseDeTabla) {
      pedidos.push(
        api.getTablaFase(edicion.id, String(activeFase.id))
          .then(data => activo && setTabla(data))
          .catch(() => activo && setTabla([]))
      );
    }
    if (!esFaseDeTabla || esFaseSuiza) {
      pedidos.push(
        api.getPartidasByFase(String(activeFase.id))
          .then(data => activo && setPartidas(data.map(p => mapPartida(p, activeFase.nombre))))
          .catch(() => activo && setPartidas([]))
      );
    }
    Promise.all(pedidos).finally(() => activo && setLoadingFaseData(false));
    return () => { activo = false; };
  }, [activeFase?.id, refreshKey]);

  const formatoTexto = activeFase ? (FORMATO_LABEL[activeFase.formato] || activeFase.formato) : '—';

  return (
    <>
      {/* HEADER HERO */}
      <section className="relative overflow-hidden bg-slate-950 border-b border-slate-800">
        <div className="absolute inset-0 bg-gradient-to-br from-violet-950/40 via-slate-950 to-cyan-950/20" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative py-10 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-purple-950/90 border border-purple-500 text-purple-300">
              {edicion.juego.nombre}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-950/90 border border-emerald-500 text-emerald-300">
              {ESTADO_LABEL[edicion.estado] || edicion.estado}
            </span>
            {activeFase && (
              <span className="text-xs font-mono text-slate-400 bg-slate-900/80 px-2.5 py-1 rounded border border-slate-800">
                Formato: {formatoTexto}
              </span>
            )}
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">{edicion.nombre}</h1>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="flex flex-wrap items-center gap-6 text-xs text-slate-300">
              {edicion.bolsaPremios && (
                <span className="flex items-center gap-2 text-amber-300 font-extrabold font-mono text-sm">
                  <Award className="w-4 h-4 text-amber-400" /> Bolsa: {edicion.bolsaPremios}
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <Users className="w-4 h-4 text-purple-400" /> {edicion.equiposInscritosCount}{edicion.maxEquipos ? ` / ${edicion.maxEquipos}` : ''} Equipos
              </span>
              {edicion.fechaInicio && (
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-cyan-400" /> Inicio: {new Date(edicion.fechaInicio).toLocaleDateString('es-BO')}
                </span>
              )}
            </div>

            {edicion.estado === 'inscripciones_abiertas' && (
              <Link
                href={`/torneos/${edicion.slug}/inscribirse`}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 hover:to-cyan-500 text-white font-bold text-xs shadow-lg shadow-violet-600/30 flex items-center gap-2 transition-all hover:scale-[1.02]"
              >
                <Trophy size={14} className="text-amber-300" /> Inscribir mi Squad
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* TABS */}
      <section className="sticky top-16 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 overflow-x-auto py-3 text-xs font-bold">
            <button
              onClick={() => setActiveTab('brackets')}
              className={`px-4 py-2 rounded-xl flex items-center gap-2 transition-all ${activeTab === 'brackets' ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-900'}`}
            >
              <Sword className="w-4 h-4" /> {esFaseDeTabla ? 'Tabla de Posiciones' : 'Cuadro de Brackets'}
            </button>
            <button
              onClick={() => setActiveTab('teams')}
              className={`px-4 py-2 rounded-xl flex items-center gap-2 transition-all ${activeTab === 'teams' ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-900'}`}
            >
              <Users className="w-4 h-4 text-cyan-400" /> Equipos ({edicion.equiposInscritosCount})
            </button>
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 rounded-xl flex items-center gap-2 transition-all ${activeTab === 'overview' ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-900'}`}
            >
              <FileText className="w-4 h-4 text-purple-400" /> Reglamento
            </button>
          </div>
        </div>
      </section>

      {/* CONTENT */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-20">
        {activeTab === 'brackets' && (
          <div className="space-y-6">
            {fases.length === 0 ? (
              <div className="bg-[#0e101d] border border-slate-800 rounded-2xl p-10 text-center text-xs text-white/40">
                {edicion.estado === 'inscripciones_abiertas'
                  ? 'Las llaves se van a sortear cuando cierren las inscripciones.'
                  : 'Este torneo todavía no tiene fases configuradas.'}
              </div>
            ) : (
              <div className="space-y-6">
                {fases.length > 1 && (
                  <div className="flex items-center gap-2 overflow-x-auto bg-[#0e101d] p-3 rounded-2xl border border-purple-500/30 shadow-lg">
                    <span className="text-xs font-black uppercase text-purple-400 px-2 flex items-center gap-1.5 shrink-0 font-mono">
                      <Layers size={15} /> Etapas ({fases.length}):
                    </span>
                    {fases.map((f, i) => (
                      <button
                        key={f.id}
                        onClick={() => setActiveFaseId(f.id)}
                        className={`px-4 py-2 rounded-xl text-xs font-bold shrink-0 transition-all ${
                          (activeFaseId ?? fases[0].id) === f.id
                            ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30 ring-1 ring-purple-400'
                            : 'bg-slate-900/80 text-slate-400 hover:text-white hover:bg-slate-800'
                        }`}
                      >
                        Paso {i + 1}: {f.nombre}
                      </button>
                    ))}
                  </div>
                )}

                {esFaseSuiza && !loadingFaseData && (
                  <div className="flex items-center gap-2 bg-[#0e101d] p-1.5 rounded-xl border border-slate-800 w-fit">
                    <button
                      onClick={() => setVistaSuizo('cruces')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${vistaSuizo === 'cruces' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                      Cruces
                    </button>
                    <button
                      onClick={() => setVistaSuizo('tabla')}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${vistaSuizo === 'tabla' ? 'bg-purple-600 text-white' : 'text-slate-400 hover:text-white'}`}
                    >
                      Tabla de Posiciones
                    </button>
                  </div>
                )}

                {loadingFaseData ? (
                  <div className="flex items-center justify-center gap-2 text-white/40 text-xs py-20">
                    <Loader2 className="animate-spin" size={16} /> Cargando datos de la fase...
                  </div>
                ) : esFaseSuiza ? (
                  vistaSuizo === 'cruces' ? (
                    <SwissBracketView
                      partidas={partidas}
                      onSelectPartida={setSelectedPartida}
                      metaVictorias={activeFase?.config?.meta_victorias}
                      metaDerrotas={activeFase?.config?.meta_derrotas}
                    />
                  ) : (
                    <GroupStageView grupos={tabla} clasificadosPorGrupo={activeFase?.config?.cupos_avance || 1} />
                  )
                ) : esFaseDeTabla ? (
                  <GroupStageView grupos={tabla} clasificadosPorGrupo={activeFase?.config?.cupos_avance || 1} />
                ) : activeFase?.formato === 'eliminacion_doble' ? (
                  <DoubleEliminationView partidas={partidas} onSelectPartida={setSelectedPartida} />
                ) : (
                  <BracketView
                    fases={[mapFase(activeFase as ApiFase, partidas)]}
                    onSelectPartida={setSelectedPartida}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'teams' && (
          <TeamsList edicionId={edicion.id} maxEquipos={edicion.maxEquipos} equiposCount={edicion.equiposInscritosCount} />
        )}

        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-6">
              <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
                <h3 className="font-extrabold text-base text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-purple-400" /> Reglamento Oficial
                </h3>
                {edicion.reglamentoUrl ? (
                  <a
                    href={edicion.reglamentoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-xs text-cyan-400 hover:text-cyan-300 font-semibold underline"
                  >
                    <FileText size={14} /> Ver reglamento completo
                  </a>
                ) : (
                  <p className="text-xs text-slate-400">El organizador todavía no publicó el reglamento de este torneo.</p>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="glass-card rounded-2xl p-6 border border-slate-800 space-y-4">
                <h4 className="font-bold text-sm text-white flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-amber-400" /> Identidad de Juego
                </h4>
                <div className="space-y-2 text-xs text-slate-300">
                  {edicion.juego.camposIdentidad.map((campo) => (
                    <div key={campo.key} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                      <span className="font-semibold text-purple-300 block">{campo.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* PARTIDA DETAIL — reporte/check-in/disputa real para capitanes logueados */}
      {selectedPartida && (
        <PartidaDetailModal
          partida={selectedPartida}
          onClose={() => setSelectedPartida(null)}
          onUpdated={() => setRefreshKey(k => k + 1)}
        />
      )}
    </>
  );
}
