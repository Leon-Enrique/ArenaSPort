'use client';

import React, { useState } from 'react';
import { Partida, Fase } from '@/types';
import { Trophy, Layers, CheckCircle2 } from 'lucide-react';

interface BracketViewProps {
  fases: Fase[];
  onSelectPartida?: (partida: Partida) => void;
}

export default function BracketView({ fases, onSelectPartida }: BracketViewProps) {
  const defaultFase = fases.find(f => f.formato === 'eliminacion_simple' || f.formato === 'eliminacion_doble') || fases[0];
  const [activeFaseId, setActiveFaseId] = useState<string>(defaultFase?.id || 'fase-bracket-main');
  const [selectedRoundFilter, setSelectedRoundFilter] = useState<number | 'all'>('all');

  const currentFase = fases.find(f => f.id === activeFaseId) || defaultFase || fases[0];
  const partidas = currentFase?.partidas || [];

  // Agrupar partidas por ronda
  const roundMap: Record<number, Partida[]> = {};
  partidas.forEach(p => {
    const r = p.numeroRonda || 1;
    if (!roundMap[r]) roundMap[r] = [];
    roundMap[r].push(p);
  });
  const roundNumbers = Object.keys(roundMap).map(Number).sort((a, b) => a - b);
  const totalRounds = roundNumbers.length || 1;
  const numR1Matches = roundMap[1]?.length || 4;
  const totalTeams = numR1Matches * 2;

  const getRoundLabel = (rondaNum: number, total: number) => {
    if (total === 1) return 'Octavos de Final';
    if (rondaNum === total) return 'Gran Final';
    if (rondaNum === total - 1) return 'Semifinales';
    if (rondaNum === total - 2) return 'Cuartos';
    if (rondaNum === total - 3) return 'Octavos';
    if (rondaNum === total - 4) return '16avos';
    return `Round ${rondaNum}`;
  };

  // Dimensiones matemáticas del árbol de brackets (Toornament Pixel-Perfect)
  const CARD_W = 210;
  const CARD_H = 64;
  const CONNECTOR_W = 42;
  const UNIT_H = totalTeams >= 64 ? 76 : totalTeams >= 32 ? 82 : 92;
  const totalTreeHeight = numR1Matches * UNIT_H;
  const totalTreeWidth = roundNumbers.length * (CARD_W + CONNECTOR_W);

  // Función matemática de centrado vertical por ronda
  const getCenterY = (rondaNum: number, matchIdx: number) => {
    const blockH = UNIT_H * Math.pow(2, rondaNum - 1);
    return matchIdx * blockH + blockH / 2;
  };

  const displayedRoundNumbers = selectedRoundFilter === 'all'
    ? roundNumbers
    : [selectedRoundFilter];

  return (
    <div className="w-full space-y-6">
      {/* ── HEADER SUPERIOR DE LA ETAPA ── */}
      <div className="bg-[#0e101d] rounded-2xl p-5 border border-slate-800 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2.5 h-2.5 rounded-full ${currentFase?.estado === 'finalizada' ? 'bg-emerald-400' : 'bg-cyan-400 animate-pulse'}`} />
              <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest font-mono">
                {currentFase?.estado === 'finalizada' ? 'Torneo Finalizado' : currentFase?.estado === 'inscripciones_abiertas' ? 'Inscripciones en Curso' : 'En Curso'} • {totalTeams} slots • {totalRounds} Ronda{totalRounds !== 1 ? 's' : ''}
              </span>
            </div>
            <h2 className="text-xl font-black text-white tracking-wide flex items-center gap-2">
              <Trophy size={20} className="text-purple-400" />
              {currentFase?.nombre || 'Cuadro de Brackets'}
            </h2>
            <div className="flex flex-wrap gap-2 mt-2">
              {(currentFase as any)?.cuposAvance > 1 && (
                <div className="inline-flex items-center gap-1.5 bg-emerald-900/30 border border-emerald-500/40 rounded-lg px-3 py-1 text-xs font-bold text-emerald-400">
                  <CheckCircle2 size={13} />
                  {(currentFase as any).cuposAvance} clasificados avanzan a la siguiente fase
                </div>
              )}
              {(currentFase as any)?.numByes > 0 && (
                <div className="inline-flex items-center gap-1.5 bg-slate-900/80 border border-slate-600/40 rounded-lg px-3 py-1 text-xs font-bold text-slate-400">
                  <span className="text-slate-300">BYE ×{(currentFase as any).numByes}</span>
                  <span className="font-normal">— Los top seeds reciben pase directo a Ronda 2</span>
                </div>
              )}
            </div>
          </div>

          {/* Selector de Etapas si hay varias */}
          {fases.length > 1 && (
            <div className="flex items-center gap-2 overflow-x-auto bg-slate-950 p-1.5 rounded-xl border border-slate-800">
              <span className="text-[11px] font-bold text-slate-500 uppercase px-2 flex items-center gap-1">
                <Layers size={13} className="text-purple-400" /> Etapas:
              </span>
              {fases.map((f) => (
                <button
                  key={f.id}
                  onClick={() => { setActiveFaseId(f.id); setSelectedRoundFilter('all'); }}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
                    activeFaseId === f.id
                      ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                      : 'text-slate-400 hover:text-white hover:bg-slate-900'
                  }`}
                >
                  <span>{f.nombre}</span>
                  <span className="text-[10px] opacity-70 font-mono">({f.partidas.length})</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Filtros de Rondas — solo mostrar si hay más de 1 ronda */}
        {totalRounds > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
            <button
              onClick={() => setSelectedRoundFilter('all')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold shrink-0 transition-all ${
                selectedRoundFilter === 'all'
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                  : 'bg-slate-900/80 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              Todo el Cuadro Conectado ({totalRounds} Rondas)
            </button>

            {roundNumbers.map((rNum) => (
              <button
                key={rNum}
                onClick={() => setSelectedRoundFilter(rNum)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold shrink-0 transition-all ${
                  selectedRoundFilter === rNum
                    ? 'bg-purple-600 text-white shadow-md'
                    : 'bg-slate-900/80 text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                Round {rNum} ({getRoundLabel(rNum, totalRounds)})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── ARBOL DE BRACKETS CON LÍNEAS CONECTORAS EXACTAS (ESTILO TOORNAMENT) ── */}
      <div className="w-full overflow-x-auto overflow-y-auto max-h-[750px] bg-[#0c0d18] rounded-2xl border border-slate-800 p-6 scrollbar-thin scrollbar-thumb-purple-600/50">
        
        {/* VISTA FILTRADA POR 1 SOLA RONDA (Columna simple) */}
        {selectedRoundFilter !== 'all' ? (
          <div className="max-w-md mx-auto space-y-3">
            <div className="text-center pb-3 border-b border-slate-800">
              <span className="text-sm font-black uppercase tracking-wider text-white">
                Round {selectedRoundFilter}: {getRoundLabel(selectedRoundFilter, totalRounds)}
              </span>
            </div>
            <div className="space-y-3">
              {(roundMap[selectedRoundFilter] || []).map((partida, mIdx) => {
                const partA = partida.participaciones[0];
                const partB = partida.participaciones[1];
                const isDone = partida.estado === 'confirmada';

                return (
                  <div
                    key={partida.id}
                    onClick={() => onSelectPartida && onSelectPartida(partida)}
                    className={`w-full overflow-hidden cursor-pointer transition-all shadow-lg ${
                      (partida as any).isBye
                        ? 'bg-slate-900/40 border border-slate-700/40 rounded-xl opacity-80 hover:opacity-100'
                        : 'bg-[#161726] hover:bg-[#1e2034] border border-[#2a2d48] hover:border-purple-500 rounded-xl'
                    }`}
                  >
                    <div className="px-3 py-1 bg-slate-950/90 border-b border-[#222438] flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span>{partida.nombreGrupo || `Match #${mIdx + 1}`}</span>
                      <span className="text-purple-400 font-bold">BO{partida.formatoBo || 3}</span>
                    </div>
                    {/* Team A */}
                    <div className={`px-3 py-2 flex items-center justify-between border-b border-[#202235] text-xs ${partA?.esGanador ? 'bg-purple-950/40' : ''}`}>
                      <span className={`font-semibold truncate text-[11px] ${partA?.esGanador ? 'text-white font-bold' : partA?.equipo ? 'text-slate-300' : 'text-slate-500 italic'}`}>
                        {partA?.equipo?.nombre || 'Por Definir'}
                      </span>
                      <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${partA?.esGanador ? 'bg-emerald-600 text-white shadow' : 'bg-slate-900 text-slate-400'}`}>
                        {partA?.mapasGanados ?? 0}
                      </span>
                    </div>
                    {/* Team B */}
                    <div className={`px-3 py-2 flex items-center justify-between text-xs ${partB?.esGanador ? 'bg-purple-950/40' : ''}`}>
                      <span className={`font-semibold truncate text-[11px] ${partB?.esGanador ? 'text-white font-bold' : partB?.equipo ? 'text-slate-300' : 'text-slate-500 italic'}`}>
                        {partB?.equipo?.nombre || 'Por Definir'}
                      </span>
                      <span className={`font-mono text-xs font-bold px-2 py-0.5 rounded ${partB?.esGanador ? 'bg-emerald-600 text-white shadow' : 'bg-slate-900 text-slate-400'}`}>
                        {partB?.mapasGanados ?? 0}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          /* VISTA COMPLETA: ARBOL CON LÍNEAS CONECTORAS */
          <div
            className="relative"
            style={{
              width: `${totalTreeWidth + 20}px`,
              height: `${totalTreeHeight + 60}px`,
              minHeight: '400px'
            }}
          >
            {roundNumbers.map((rondaNum, rIdx) => {
              const matches = roundMap[rondaNum] || [];
              const isLast = rIdx === roundNumbers.length - 1;
              const leftPos = rIdx * (CARD_W + CONNECTOR_W);

              return (
                <React.Fragment key={rondaNum}>
                  
                  {/* Encabezado de la Ronda */}
                  <div
                    className="absolute text-center"
                    style={{
                      left: `${leftPos}px`,
                      top: '0px',
                      width: `${CARD_W}px`
                    }}
                  >
                    <span className="text-[11px] font-black uppercase tracking-wider text-slate-300 block">
                      Round {rondaNum}
                    </span>
                    <span className="text-[10px] text-purple-400 font-semibold font-mono">
                      {getRoundLabel(rondaNum, totalRounds)}
                    </span>
                  </div>

                  {/* Tarjetas de Partidas de la Ronda */}
                  {matches.map((partida, mIdx) => {
                    const centerY = getCenterY(rondaNum, mIdx) + 36; // +36 offset del header
                    const topPos = centerY - CARD_H / 2;
                    const partA = partida.participaciones[0];
                    const partB = partida.participaciones[1];
                    const isDone = partida.estado === 'confirmada';

                    return (
                      <div
                        key={partida.id}
                        onClick={() => onSelectPartida && onSelectPartida(partida)}
                        className={`absolute rounded-xl overflow-hidden cursor-pointer transition-all shadow-xl group z-10 ${
                          (partida as any).isBye
                            ? 'bg-slate-900/50 border border-slate-700/50 opacity-75 hover:opacity-100'
                            : 'bg-[#161726] hover:bg-[#1e2034] border border-[#272a42] hover:border-purple-500'
                        }`}
                        style={{
                          left: `${leftPos}px`,
                          top: `${topPos}px`,
                          width: `${CARD_W}px`,
                          height: `${CARD_H}px`
                        }}
                      >
                        {/* TEAM A */}
                        <div className={`px-2.5 h-[31px] flex items-center justify-between border-b border-[#202235] text-xs ${
                          partA?.esGanador && !(partida as any).isBye ? 'bg-purple-950/40' : ''
                        }`}>
                          <span className={`truncate max-w-[145px] text-[11px] ${
                            (partida as any).isBye
                              ? 'text-slate-400 font-semibold'
                              : partA?.esGanador
                              ? 'text-white font-black'
                              : partA?.equipo
                              ? 'text-slate-300 font-medium'
                              : 'text-slate-500 italic'
                          }`}>
                            {(partida as any).isBye ? (partA?.equipo?.nombre || 'Seed #?') : (partA?.equipo?.nombre || 'Por Definir')}
                          </span>
                          {(partida as any).isBye ? (
                            <span className="text-[9px] font-bold bg-cyan-900/60 text-cyan-400 border border-cyan-700/40 px-1.5 rounded font-mono">BYE ✓</span>
                          ) : (
                            <span className={`font-mono text-xs font-bold px-1.5 py-0.2 rounded min-w-[20px] text-center ${
                              partA?.esGanador ? 'bg-emerald-500 text-slate-950 font-black shadow' : isDone ? 'text-slate-400 bg-slate-900/80' : 'text-slate-600 bg-slate-900/30'
                            }`}>
                              {partA?.mapasGanados ?? 0}
                            </span>
                          )}
                        </div>

                        {/* TEAM B */}
                        <div className="px-2.5 h-[31px] flex items-center justify-between text-xs">
                          <span className="truncate max-w-[145px] text-[11px] text-slate-600 italic font-mono">
                            {(partida as any).isBye ? '— BYE —' : (partB?.equipo?.nombre || 'Por Definir')}
                          </span>
                          {!(partida as any).isBye && (
                            <span className={`font-mono text-xs font-bold px-1.5 py-0.2 rounded min-w-[20px] text-center ${
                              partB?.esGanador ? 'bg-emerald-500 text-slate-950 font-black shadow' : isDone ? 'text-slate-400 bg-slate-900/80' : 'text-slate-600 bg-slate-900/30'
                            }`}>
                              {partB?.mapasGanados ?? 0}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  {/* ── LÍNEAS CONECTORAS SVG HACIA LA SIGUIENTE RONDA ── */}
                  {!isLast && (
                    <svg
                      className="absolute pointer-events-none z-0"
                      style={{
                        left: `${leftPos + CARD_W}px`,
                        top: '36px',
                        width: `${CONNECTOR_W}px`,
                        height: `${totalTreeHeight}px`
                      }}
                    >
                      {Array.from({ length: Math.floor(matches.length / 2) }).map((_, pairIdx) => {
                        const upperCenterY = getCenterY(rondaNum, pairIdx * 2);
                        const lowerCenterY = getCenterY(rondaNum, pairIdx * 2 + 1);
                        const midY = (upperCenterY + lowerCenterY) / 2;
                        const midX = CONNECTOR_W / 2;

                        return (
                          <g key={pairIdx} stroke="#475569" strokeWidth="1.75" fill="none">
                            {/* Brazo superior saliendo de Match Superior */}
                            <path d={`M 0 ${upperCenterY} L ${midX} ${upperCenterY}`} />
                            
                            {/* Brazo inferior saliendo de Match Inferior */}
                            <path d={`M 0 ${lowerCenterY} L ${midX} ${lowerCenterY}`} />
                            
                            {/* Tronco vertical que une ambos brazos */}
                            <path d={`M ${midX} ${upperCenterY} L ${midX} ${lowerCenterY}`} />
                            
                            {/* Brazo horizontal saliendo del punto medio hacia el Match de la siguiente ronda */}
                            <path d={`M ${midX} ${midY} L ${CONNECTOR_W} ${midY}`} />
                          </g>
                        );
                      })}
                    </svg>
                  )}

                </React.Fragment>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}
