'use client';

import React, { useState } from 'react';
import { Partida } from '@/types';
import { Trophy, Shield, Flame, Crown, ArrowRight, ChevronDown } from 'lucide-react';

interface DoubleEliminationViewProps {
  partidas: Partida[];
  onSelectPartida?: (partida: Partida) => void;
}

function MatchCard({ partida, onClick, isGF = false }: { partida: Partida; onClick?: () => void; isGF?: boolean }) {
  const partA = partida.participaciones[0];
  const partB = partida.participaciones[1];
  const isDone = partida.estado === 'confirmada';

  return (
    <div
      onClick={onClick}
      className={`w-[220px] rounded-[6px] overflow-hidden cursor-pointer transition-all shadow-xl group border shrink-0 ${
        isGF
          ? 'border-amber-500/80 bg-elevada hover:border-amber-400 shadow-amber-500/20'
          : 'border-[#2a2d48] bg-[#161726] hover:border-acento hover:bg-[#1e2034]'
      }`}
    >
      <div className="px-2.5 py-1 bg-fondo/90 border-b border-[#222438] flex items-center justify-between text-[10px] text-tinta-3 font-mono">
        <span className="truncate max-w-[135px]">{partida.nombreGrupo}</span>
        <span className={`font-bold ${isGF ? 'text-atencion' : 'text-acento-claro'}`}>BO{partida.formatoBo || 3}</span>
      </div>
      {[partA, partB].map((part, idx) => (
        <div
          key={idx}
          className={`px-2.5 h-[30px] flex items-center justify-between text-xs ${idx === 0 ? 'border-b border-[#202235]' : ''} ${part?.esGanador ? (isGF ? 'bg-amber-900/30' : 'bg-elevada') : ''}`}
        >
          <span className={`truncate max-w-[160px] text-[11px] ${
            part?.esGanador ? 'text-white font-black' : part?.equipo ? 'text-tinta-2 font-medium' : 'text-tinta-4 italic'
          }`}>
            {part?.equipo?.nombre || 'Por Definir'}
          </span>
          <span className={`font-mono text-xs font-bold px-1.5 rounded min-w-[20px] text-center ${
            part?.esGanador
              ? (isGF ? 'bg-amber-500 text-fondo font-black' : 'bg-emerald-500 text-fondo font-black')
              : isDone ? 'text-tinta-3 bg-superficie' : 'text-tinta-4 bg-superficie/30'
          }`}>
            {part?.mapasGanados ?? 0}
          </span>
        </div>
      ))}
    </div>
  );
}

// Flecha de transición entre rondas
function FlowArrow({ label, color = 'text-tinta-4' }: { label?: string; color?: string }) {
  return (
    <div className={`flex flex-col items-center justify-center mx-1 shrink-0 gap-0.5 ${color}`}>
      <ArrowRight size={16} className="opacity-60" />
      {label && <span className="text-[9px] font-mono opacity-50 whitespace-nowrap">{label}</span>}
    </div>
  );
}

// Flecha hacia abajo indicando caída al LB
function DropArrow({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-1 text-orange-400/60 text-[10px] font-mono">
      <ChevronDown size={12} />
      {label && <span>{label}</span>}
    </div>
  );
}

interface BracketLaneProps {
  label: string;
  icon: React.ReactNode;
  headerColor: string;
  borderColor: string;
  rounds: { label: string; matches: Partida[] }[];
  onSelectPartida?: (p: Partida) => void;
  dropLabels?: (string | null)[]; // etiquetas entre rondas
}

function BracketLane({ label, icon, headerColor, borderColor, rounds, onSelectPartida, dropLabels = [] }: BracketLaneProps) {
  return (
    <div className={`rounded-[6px] border ${borderColor} bg-fondo/60 overflow-hidden`}>
      {/* Lane Header */}
      <div className={`px-4 py-2.5 border-b ${borderColor} ${headerColor} flex items-center gap-2`}>
        {icon}
        <span className="text-sm font-black uppercase tracking-wider text-white">{label}</span>
      </div>

      {/* Rounds + Arrows */}
      <div className="p-4 flex items-start gap-2 overflow-x-auto">
        {rounds.map((round, rIdx) => (
          <React.Fragment key={rIdx}>
            {/* Round Column */}
            <div className="flex flex-col shrink-0">
              {/* Round Label */}
              <div className="text-center mb-2">
                <span className="text-[10px] font-black uppercase tracking-wider text-tinta-4 block font-mono">
                  {round.label}
                </span>
              </div>
              {/* Matches - centered vertically relative to next round */}
              <div className="flex flex-col gap-3">
                {round.matches.map((match) => (
                  <MatchCard
                    key={match.id}
                    partida={match}
                    onClick={() => onSelectPartida && onSelectPartida(match)}
                  />
                ))}
              </div>
            </div>

            {/* Arrow between rounds */}
            {rIdx < rounds.length - 1 && (
              <div className="flex flex-col justify-center pt-6">
                <FlowArrow label={dropLabels[rIdx] || undefined} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export default function DoubleEliminationView({ partidas, onSelectPartida }: DoubleEliminationViewProps) {
  const [activeView, setActiveView] = useState<'all' | 'upper' | 'lower' | 'gf'>('all');

  const ubMatches = partidas.filter((p: any) => p.bracket === 'upper');
  const lbMatches = partidas.filter((p: any) => p.bracket === 'lower');
  const gfMatches = partidas.filter((p: any) => p.bracket === 'grand_final');

  // Agrupar UB por ronda (1=QF, 2=SF, 3=Final)
  const ubR1 = ubMatches.filter(p => p.numeroRonda === 1);
  const ubR2 = ubMatches.filter(p => p.numeroRonda === 2);
  const ubR3 = ubMatches.filter(p => p.numeroRonda === 3);

  // Agrupar LB por ronda
  const lbR1 = lbMatches.filter(p => p.numeroRonda === 1);
  const lbR2 = lbMatches.filter(p => p.numeroRonda === 2);
  const lbR3 = lbMatches.filter(p => p.numeroRonda === 3);
  const lbR4 = lbMatches.filter(p => p.numeroRonda === 4);

  // Campeón
  const gfMatch = gfMatches[0];
  const champion = gfMatch?.participaciones.find(p => p.esGanador);

  const ubRounds = [
    ...(ubR1.length > 0 ? [{ label: 'Cuartos de Final', matches: ubR1 }] : []),
    ...(ubR2.length > 0 ? [{ label: 'Semifinales', matches: ubR2 }] : []),
    ...(ubR3.length > 0 ? [{ label: 'UB Final', matches: ubR3 }] : []),
  ];

  const lbRounds = [
    ...(lbR1.length > 0 ? [{ label: 'LB R1', matches: lbR1 }] : []),
    ...(lbR2.length > 0 ? [{ label: 'LB R2', matches: lbR2 }] : []),
    ...(lbR3.length > 0 ? [{ label: 'LB Semis', matches: lbR3 }] : []),
    ...(lbR4.length > 0 ? [{ label: 'LB Final', matches: lbR4 }] : []),
  ];

  const tabs = [
    { id: 'all' as const, label: '📋 Vista Completa' },
    { id: 'upper' as const, label: '🔺 Upper Bracket' },
    { id: 'lower' as const, label: '🔻 Lower Bracket' },
    { id: 'gf' as const, label: '🏆 Gran Final' },
  ];

  return (
    <div className="space-y-5">
      {/* CAMPEÓN BANNER */}
      {champion && (
        <div className="bg-elevada border border-amber-500/50 rounded-[6px] p-5 flex items-center gap-4 shadow-2xl shadow-amber-500/10">
          <div className="w-14 h-14 rounded-full bg-elevada flex items-center justify-center shadow-lg shadow-amber-500/30 shrink-0">
            <Crown size={28} className="text-slate-900" />
          </div>
          <div>
            <span className="text-xs font-bold text-atencion uppercase tracking-widest block mb-0.5 font-mono">🏆 Campeón del Torneo</span>
            <span className="text-2xl font-black text-white tracking-tight">{champion.equipo?.nombre}</span>
            <span className="text-xs text-atencion/70 block mt-0.5">Doble Eliminación • Gran Final BO5 🎖️</span>
          </div>
        </div>
      )}

      {/* TABS */}
      <div className="flex items-center gap-2 bg-[#0e101d] p-2 rounded-[6px] border border-borde overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveView(tab.id)}
            className={`px-4 py-2 rounded-[4px] text-xs font-bold shrink-0 transition-all ${
              activeView === tab.id
                ? 'bg-acento text-white'
                : 'text-tinta-3 hover:text-white hover:bg-elevada'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* UPPER BRACKET */}
      {(activeView === 'all' || activeView === 'upper') && ubRounds.length > 0 && (
        <BracketLane
          label="Upper Bracket — Winners"
          icon={<Shield size={16} className="text-acento-claro" />}
          headerColor="bg-elevada"
          borderColor="border-acento/40"
          rounds={ubRounds}
          onSelectPartida={onSelectPartida}
          dropLabels={['ganador avanza', 'ganador avanza']}
        />
      )}

      {/* FLUJO UPPER → LOWER */}
      {(activeView === 'all') && ubRounds.length > 0 && lbRounds.length > 0 && (
        <div className="flex items-center gap-3 px-4 text-[11px] text-orange-400/70 font-mono">
          <div className="flex-1 border-t border-dashed border-orange-500/20" />
          <span className="flex items-center gap-1.5 bg-orange-950/30 border border-orange-500/30 rounded-[4px] px-3 py-1.5 shrink-0">
            <ChevronDown size={13} />
            Los perdedores del Upper Bracket caen al Lower Bracket
          </span>
          <div className="flex-1 border-t border-dashed border-orange-500/20" />
        </div>
      )}

      {/* LOWER BRACKET */}
      {(activeView === 'all' || activeView === 'lower') && lbRounds.length > 0 && (
        <BracketLane
          label="Lower Bracket — Losers"
          icon={<Flame size={16} className="text-orange-400" />}
          headerColor="bg-orange-950/40"
          borderColor="border-orange-500/40"
          rounds={lbRounds}
          onSelectPartida={onSelectPartida}
          dropLabels={['avanza', 'avanza', 'avanza']}
        />
      )}

      {/* FLUJO LOWER → GF */}
      {(activeView === 'all') && lbRounds.length > 0 && gfMatches.length > 0 && (
        <div className="flex items-center gap-3 px-4 text-[11px] text-atencion/70 font-mono">
          <div className="flex-1 border-t border-dashed border-amber-500/20" />
          <span className="flex items-center gap-1.5 bg-amber-950/30 border border-amber-500/30 rounded-[4px] px-3 py-1.5 shrink-0">
            <ArrowRight size={13} />
            Ganador LB Final vs Campeón UB → Gran Final BO5
          </span>
          <div className="flex-1 border-t border-dashed border-amber-500/20" />
        </div>
      )}

      {/* GRAN FINAL */}
      {(activeView === 'all' || activeView === 'gf') && gfMatches.length > 0 && (
        <div className="rounded-[6px] border border-amber-500/50 bg-amber-950/20 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-amber-500/30 bg-amber-900/20 flex items-center gap-2">
            <Trophy size={16} className="text-atencion" />
            <span className="text-sm font-black uppercase tracking-wider text-atencion">Gran Final — Best of 5</span>
            <span className="text-xs text-amber-500/60 font-mono ml-2">UB Champion vs LB Champion</span>
          </div>
          <div className="p-6 flex justify-center">
            <div className="flex flex-col items-center gap-3">
              {gfMatches.map(p => (
                <MatchCard
                  key={p.id}
                  partida={p}
                  isGF
                  onClick={() => onSelectPartida && onSelectPartida(p)}
                />
              ))}
              {champion && (
                <div className="flex items-center gap-2 mt-2 text-atencion text-sm font-black">
                  <Crown size={16} />
                  <span>{champion.equipo?.nombre} — CAMPEÓN 🏆</span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* LEYENDA */}
      <div className="flex flex-wrap items-center gap-4 text-[11px] text-tinta-4 px-1 pt-1">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-emerald-500 shrink-0" />
          <span>Score (Ganador)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded border border-acento/60 shrink-0" />
          <span>Upper Bracket — ganar o caer al Lower</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded border border-orange-500/60 shrink-0" />
          <span>Lower Bracket — una vida más, pierde = eliminado</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded bg-amber-600/60 shrink-0" />
          <span>Gran Final BO5 — UB Campeón vs LB Campeón</span>
        </div>
      </div>
    </div>
  );
}
