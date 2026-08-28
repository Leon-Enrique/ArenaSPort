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
import { escucharEdicion } from '@/lib/eventos';
import { ApiFase, ApiResumenEdicion, ApiTablaGrupo } from '@/lib/api-types';
import { Partida } from '@/types';
import {
  Trophy, Shield, Users, Calendar, Award, FileText,
  Sword, Layers, Loader2, Radio,
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

  // Bracket en vivo. El evento solo dice QUÉ partida cambió, no cómo quedó:
  // se vuelve a pedir la fase para que el permiso de quien mira lo siga
  // decidiendo el endpoint de siempre y no el stream.
  //
  // Solo se refresca si el cambio es de la fase que se está viendo. Sin ese
  // filtro, un torneo con varias fases activas recargaría la pantalla por
  // partidas de otra etapa que ni se ven.
  const [enVivo, setEnVivo] = useState(false);

  useEffect(() => {
    return escucharEdicion(
      edicion.id,
      (evento) => {
        if (!activeFase || evento.fase_id === activeFase.id) {
          setRefreshKey(k => k + 1);
        }
      },
      setEnVivo,
    );
  }, [edicion.id, activeFase?.id]);

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
      <section className="bg-fondo border-b border-borde-sutil">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-elevada/90 border border-acento text-acento-claro">
              {edicion.juego.nombre}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-950/90 border border-emerald-500 text-ok">
              {ESTADO_LABEL[edicion.estado] || edicion.estado}
            </span>
            {activeFase && (
              <span className="text-xs font-mono text-tinta-3 bg-superficie px-2.5 py-1 rounded border border-borde">
                Formato: {formatoTexto}
              </span>
            )}
            {enVivo && (
              <span
                title="Los resultados se actualizan solos, sin recargar la página."
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-950/60 border border-rose-500/40 text-vivo"
              >
                <Radio size={11} className="animate-pulse" /> EN VIVO
              </span>
            )}
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">{edicion.nombre}</h1>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
            <div className="flex flex-wrap items-center gap-6 text-xs text-tinta-2">
              {edicion.bolsaPremios && (
                <span className="flex items-center gap-2 text-atencion font-extrabold font-mono text-sm">
                  <Award className="w-4 h-4 text-atencion" /> Bolsa: {edicion.bolsaPremios}
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <Users className="w-4 h-4 text-acento-claro" /> {edicion.equiposInscritosCount}{edicion.maxEquipos ? ` / ${edicion.maxEquipos}` : ''} Equipos
              </span>
              {edicion.fechaInicio && (
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-tinta-2" /> Inicio: {new Date(edicion.fechaInicio).toLocaleDateString('es-BO')}
                </span>
              )}
            </div>

            {edicion.estado === 'inscripciones_abiertas' && (
              <Link
                href={`/torneos/${edicion.slug}/inscribirse`}
                className="px-5 py-2.5 rounded-[6px] bg-acento text-white font-bold text-xs flex items-center gap-2 transition-all hover:scale-[1.02]"
              >
                <Trophy size={14} className="text-atencion" /> Inscribir mi Squad
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* TABS */}
      <section className="sticky top-16 z-40 bg-fondo/90 backdrop-blur-md border-b border-borde">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 overflow-x-auto py-3 text-xs font-bold">
            <button
              onClick={() => setActiveTab('brackets')}
              className={`px-4 py-2 rounded-[6px] flex items-center gap-2 transition-all ${activeTab === 'brackets' ? 'bg-acento text-white' : 'text-tinta-3 hover:text-white hover:bg-superficie'}`}
            >
              <Sword className="w-4 h-4" /> {esFaseDeTabla ? 'Tabla de Posiciones' : 'Cuadro de Brackets'}
            </button>
            <button
              onClick={() => setActiveTab('teams')}
              className={`px-4 py-2 rounded-[6px] flex items-center gap-2 transition-all ${activeTab === 'teams' ? 'bg-acento text-white' : 'text-tinta-3 hover:text-white hover:bg-superficie'}`}
            >
              <Users className="w-4 h-4 text-tinta-2" /> Equipos ({edicion.equiposInscritosCount})
            </button>
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 rounded-[6px] flex items-center gap-2 transition-all ${activeTab === 'overview' ? 'bg-acento text-white' : 'text-tinta-3 hover:text-white hover:bg-superficie'}`}
            >
              <FileText className="w-4 h-4 text-acento-claro" /> Reglamento
            </button>
          </div>
        </div>
      </section>

      {/* CONTENT */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-20">
        {activeTab === 'brackets' && (
          <div className="space-y-6">
            {fases.length === 0 ? (
              <div className="bg-[#0e101d] border border-borde rounded-[6px] p-10 text-center text-xs text-tinta-3">
                {edicion.estado === 'inscripciones_abiertas'
                  ? 'Las llaves se van a sortear cuando cierren las inscripciones.'
                  : 'Este torneo todavía no tiene fases configuradas.'}
              </div>
            ) : (
              <div className="space-y-6">
                {fases.length > 1 && (
                  <div className="flex items-center gap-2 overflow-x-auto bg-[#0e101d] p-3 rounded-[6px] border border-acento/30 shadow-lg">
                    <span className="text-xs font-black uppercase text-acento-claro px-2 flex items-center gap-1.5 shrink-0 font-mono">
                      <Layers size={15} /> Etapas ({fases.length}):
                    </span>
                    {fases.map((f, i) => (
                      <button
                        key={f.id}
                        onClick={() => setActiveFaseId(f.id)}
                        className={`px-4 py-2 rounded-[6px] text-xs font-bold shrink-0 transition-all ${
                          (activeFaseId ?? fases[0].id) === f.id
                            ? 'bg-acento text-white ring-1 ring-purple-400'
                            : 'bg-superficie text-tinta-3 hover:text-white hover:bg-elevada'
                        }`}
                      >
                        Paso {i + 1}: {f.nombre}
                      </button>
                    ))}
                  </div>
                )}

                {esFaseSuiza && !loadingFaseData && (
                  <div className="flex items-center gap-2 bg-[#0e101d] p-1.5 rounded-[6px] border border-borde w-fit">
                    <button
                      onClick={() => setVistaSuizo('cruces')}
                      className={`px-3.5 py-1.5 rounded-[4px] text-xs font-bold transition-all ${vistaSuizo === 'cruces' ? 'bg-acento text-white' : 'text-tinta-3 hover:text-white'}`}
                    >
                      Cruces
                    </button>
                    <button
                      onClick={() => setVistaSuizo('tabla')}
                      className={`px-3.5 py-1.5 rounded-[4px] text-xs font-bold transition-all ${vistaSuizo === 'tabla' ? 'bg-acento text-white' : 'text-tinta-3 hover:text-white'}`}
                    >
                      Tabla de Posiciones
                    </button>
                  </div>
                )}

                {loadingFaseData ? (
                  <div className="flex items-center justify-center gap-2 text-tinta-3 text-xs py-20">
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
              <div className="glass-card rounded-[6px] p-6 border border-borde space-y-4">
                <h3 className="font-extrabold text-base text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-acento-claro" /> Reglamento Oficial
                </h3>
                {edicion.reglamentoUrl ? (
                  <a
                    href={edicion.reglamentoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-xs text-tinta-2 hover:text-tinta-2 font-semibold underline"
                  >
                    <FileText size={14} /> Ver reglamento completo
                  </a>
                ) : (
                  <p className="text-xs text-tinta-3">El organizador todavía no publicó el reglamento de este torneo.</p>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <div className="glass-card rounded-[6px] p-6 border border-borde space-y-4">
                <h4 className="font-bold text-sm text-white flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-atencion" /> Identidad de Juego
                </h4>
                <div className="space-y-2 text-xs text-tinta-2">
                  {edicion.juego.camposIdentidad.map((campo) => (
                    <div key={campo.key} className="bg-fondo p-2.5 rounded-[4px] border border-borde">
                      <span className="font-semibold text-acento-claro block">{campo.label}</span>
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
