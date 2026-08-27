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
      <div className="bg-superficie rounded-[6px] p-5 border border-borde space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-borde-sutil pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-[5px] h-[5px] rounded-full ${currentFase?.estado === 'finalizada' ? 'bg-tinta-4' : 'bg-vivo punto-vivo'}`} />
              <span className="text-[10px] font-semibold text-tinta-3 uppercase tracking-[0.08em]">
                {currentFase?.estado === 'finalizada' ? 'Torneo Finalizado' : currentFase?.estado === 'inscripciones_abiertas' ? 'Inscripciones en Curso' : 'En Curso'} • {totalTeams} slots • {totalRounds} Ronda{totalRounds !== 1 ? 's' : ''}
              </span>
            </div>
            <h2 className="text-[18px] font-semibold text-tinta tracking-[-0.02em] mt-0.5">
              {currentFase?.nombre || 'Cuadro'}
            </h2>
            <div className="flex flex-wrap gap-2 mt-2">
              {(currentFase as any)?.cuposAvance > 1 && (
                <div className="inline-flex items-center gap-1.5 bg-superficie border border-borde rounded-[4px] px-2.5 py-1 text-[11.5px] text-tinta-2">
                  <CheckCircle2 size={13} />
                  {(currentFase as any).cuposAvance} clasificados avanzan a la siguiente fase
                </div>
              )}
              {(currentFase as any)?.numByes > 0 && (
                <div className="inline-flex items-center gap-1.5 bg-superficie border border-borde rounded-[4px] px-2.5 py-1 text-[11.5px] text-tinta-3">
                  <span className="text-tinta-2">BYE ×{(currentFase as any).numByes}</span>
                  <span className="font-normal">— Los top seeds reciben pase directo a Ronda 2</span>
                </div>
              )}
            </div>
          </div>

          {/* Selector de Etapas si hay varias */}
          {fases.length > 1 && (
            <div className="flex items-center gap-1 overflow-x-auto">
              <span className="text-[10px] font-semibold text-tinta-3 uppercase tracking-[0.08em] px-1">
                Etapas
              </span>
              {fases.map((f) => (
                <button
                  key={f.id}
                  onClick={() => { setActiveFaseId(f.id); setSelectedRoundFilter('all'); }}
                  className={`px-3 py-1.5 rounded-[4px] text-[12px] font-medium transition-colors flex items-center gap-1.5 ${
                    activeFaseId === f.id
                      ? 'bg-borde text-tinta'
                      : 'text-tinta-3 hover:text-tinta hover:bg-elevada'
                  }`}
                >
                  <span>{f.nombre}</span>
                  <span className="text-[10px] text-tinta-4 font-mono tabular">({f.partidas.length})</span>
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
              className={`px-3 py-1.5 rounded-[4px] text-[12px] font-medium shrink-0 transition-colors ${
                selectedRoundFilter === 'all'
                  ? 'bg-borde text-tinta'
                  : 'text-tinta-3 hover:text-tinta hover:bg-elevada'
              }`}
            >
              Todo el Cuadro Conectado ({totalRounds} Rondas)
            </button>

            {roundNumbers.map((rNum) => (
              <button
                key={rNum}
                onClick={() => setSelectedRoundFilter(rNum)}
                className={`px-3 py-1.5 rounded-[4px] text-[12px] font-medium shrink-0 transition-colors ${
                  selectedRoundFilter === rNum
                    ? 'bg-borde text-tinta'
                    : 'text-tinta-3 hover:text-tinta hover:bg-elevada'
                }`}
              >
                Round {rNum} ({getRoundLabel(rNum, totalRounds)})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── ARBOL DE BRACKETS CON LÍNEAS CONECTORAS EXACTAS (ESTILO TOORNAMENT) ── */}
      <div className="w-full overflow-x-auto overflow-y-auto max-h-[750px] bg-hundida rounded-[6px] border border-borde p-6">
        
        {/* VISTA FILTRADA POR 1 SOLA RONDA (Columna simple) */}
        {selectedRoundFilter !== 'all' ? (
          <div className="max-w-md mx-auto space-y-3">
            <div className="text-center pb-3 border-b border-borde">
              <span className="text-[13px] font-semibold text-tinta">
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
                        : 'bg-superficie hover:bg-elevada border border-borde hover:border-borde-fuerte rounded-[4px]'
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
                        className={`absolute rounded-[4px] overflow-hidden cursor-pointer transition-colors group z-10 ${
                          (partida as any).isBye
                            ? 'bg-hundida border border-borde-sutil'
                            : 'bg-superficie hover:bg-elevada border border-borde hover:border-borde-fuerte'
                        }`}
                        style={{
                          left: `${leftPos}px`,
                          top: `${topPos}px`,
                          width: `${CARD_W}px`,
                          height: `${CARD_H}px`
                        }}
                      >
                        {/* El ganador se marca atenuando al perdedor, no
                            pintándole el marcador de verde: en una llave de
                            16 partidas, 16 chips verdes tapan el cuadro. */}
                        <div className="px-2.5 h-[31px] flex items-center justify-between border-b border-borde-sutil">
                          <span className={`truncate max-w-[145px] text-[11.5px] ${
                            (partida as any).isBye
                              ? 'text-tinta-2 font-medium'
                              : partA?.esGanador
                              ? 'text-tinta font-semibold'
                              : partA?.equipo
                              ? isDone ? 'text-tinta-3' : 'text-tinta-2'
                              : 'text-tinta-4'
                          }`}>
                            {(partida as any).isBye ? (partA?.equipo?.nombre || 'Seed #?') : (partA?.equipo?.nombre || 'Por definir')}
                          </span>
                          {(partida as any).isBye ? (
                            <span className="text-[9px] font-semibold uppercase tracking-[0.06em] text-tinta-3">Bye</span>
                          ) : (
                            <span className={`font-mono tabular text-[12.5px] min-w-[18px] text-center ${
                              partA?.esGanador ? 'text-tinta font-semibold' : isDone ? 'text-tinta-3' : 'text-tinta-4'
                            }`}>
                              {isDone || partA?.mapasGanados ? (partA?.mapasGanados ?? 0) : '–'}
                            </span>
                          )}
                        </div>

                        <div className="px-2.5 h-[31px] flex items-center justify-between">
                          <span className={`truncate max-w-[145px] text-[11.5px] ${
                            (partida as any).isBye
                              ? 'text-tinta-4'
                              : partB?.esGanador
                              ? 'text-tinta font-semibold'
                              : partB?.equipo
                              ? isDone ? 'text-tinta-3' : 'text-tinta-2'
                              : 'text-tinta-4'
                          }`}>
                            {(partida as any).isBye ? 'Pasa directo' : (partB?.equipo?.nombre || 'Por definir')}
                          </span>
                          {!(partida as any).isBye && (
                            <span className={`font-mono tabular text-[12.5px] min-w-[18px] text-center ${
                              partB?.esGanador ? 'text-tinta font-semibold' : isDone ? 'text-tinta-3' : 'text-tinta-4'
                            }`}>
                              {isDone || partB?.mapasGanados ? (partB?.mapasGanados ?? 0) : '–'}
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
