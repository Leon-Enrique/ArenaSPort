'use client';

import React, { useState } from 'react';
import { MOCK_FREE_FIRE_STANDINGS } from '@/lib/mock-data';
import { Trophy, Award, Flame, ChevronDown, ChevronUp, Shield, Zap } from 'lucide-react';

export default function StandingsTable() {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const toggleRow = (rank: number) => {
    setExpandedRow(expandedRow === rank ? null : rank);
  };

  const getRankBadge = (rank: number) => {
    switch (rank) {
      case 1:
        return (
          <span className="w-6 h-6 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-300 text-slate-950 font-extrabold text-xs flex items-center justify-center shadow-lg shadow-amber-500/30">
            1
          </span>
        );
      case 2:
        return (
          <span className="w-6 h-6 rounded-full bg-gradient-to-tr from-slate-400 to-slate-200 text-slate-950 font-extrabold text-xs flex items-center justify-center">
            2
          </span>
        );
      case 3:
        return (
          <span className="w-6 h-6 rounded-full bg-gradient-to-tr from-amber-700 to-amber-500 text-white font-extrabold text-xs flex items-center justify-center">
            3
          </span>
        );
      default:
        return (
          <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-400 font-mono text-xs flex items-center justify-center">
            {rank}
          </span>
        );
    }
  };

  return (
    <div className="w-full space-y-4">
      
      {/* Header Info */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 glass-card rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <Trophy className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm text-white flex items-center gap-2">
              Tabla de Posiciones Acumulativa <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Free Fire BR</span>
            </h3>
            <p className="text-xs text-slate-400">Puntaje total = Puntos por posición + 1 punto por cada baja (kill)</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-amber-300 font-semibold bg-amber-950/40 px-3 py-1.5 rounded-lg border border-amber-800/40">
            <Award className="w-4 h-4 text-amber-400" /> Booyahs Registrados
          </span>
          <span className="flex items-center gap-1.5 text-rose-400 font-semibold bg-rose-950/40 px-3 py-1.5 rounded-lg border border-rose-800/40">
            <Flame className="w-4 h-4 text-rose-400" /> Bajas Totales
          </span>
        </div>
      </div>

      {/* Standings Table */}
      <div className="glass-card rounded-xl overflow-hidden border border-slate-800">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            
            {/* Table Head */}
            <thead className="bg-slate-950/90 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4 text-center">Pos</th>
                <th className="py-3 px-4">Equipo</th>
                <th className="py-3 px-4 text-center">Booyahs</th>
                <th className="py-3 px-4 text-center">Kills</th>
                <th className="py-3 px-4 text-center font-bold text-amber-400">Pts Totales</th>
                <th className="py-3 px-4 text-center">Detalle</th>
              </tr>
            </thead>

            {/* Table Body */}
            <tbody className="divide-y divide-slate-800/60">
              {MOCK_FREE_FIRE_STANDINGS.map((row) => {
                const isExpanded = expandedRow === row.rank;

                return (
                  <React.Fragment key={row.rank}>
                    <tr
                      onClick={() => toggleRow(row.rank)}
                      className={`cursor-pointer transition-colors hover:bg-slate-800/50 ${
                        row.rank === 1 ? 'bg-amber-950/10' : row.rank <= 3 ? 'bg-slate-900/30' : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-center font-bold">
                        <div className="flex items-center justify-center">
                          {getRankBadge(row.rank)}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center font-bold text-xs text-purple-400">
                            {row.equipo.tag}
                          </div>
                          <div>
                            <p className="font-bold text-slate-200">{row.equipo.nombre}</p>
                            <p className="text-[10px] text-slate-400">Capitán: {row.equipo.capitanNombre}</p>
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-4 text-center font-mono font-bold text-amber-400">
                        {row.booyahs > 0 ? (
                          <span className="inline-flex items-center gap-1 bg-amber-950/60 border border-amber-700/50 px-2 py-0.5 rounded text-amber-300">
                            <Trophy className="w-3 h-3 text-amber-400" /> {row.booyahs}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>

                      <td className="py-3 px-4 text-center font-mono font-bold text-rose-400">
                        <span className="inline-flex items-center gap-1 bg-rose-950/40 border border-rose-800/40 px-2 py-0.5 rounded">
                          <Flame className="w-3 h-3 text-rose-400" /> {row.totalKills}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-center">
                        <span className="font-mono text-sm font-extrabold text-amber-300 text-glow-gold bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/30">
                          {row.totalPts} pts
                        </span>
                      </td>

                      <td className="py-3 px-4 text-center text-slate-400">
                        <button className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition-colors">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </td>
                    </tr>

                    {/* Collapsible Caídas Details */}
                    {isExpanded && (
                      <tr className="bg-slate-950/80 border-b border-slate-800">
                        <td colSpan={6} className="p-4">
                          <div className="bg-slate-900/90 rounded-lg p-3 border border-slate-800 space-y-2">
                            <h4 className="font-semibold text-xs text-purple-300 flex items-center gap-2">
                              <Zap className="w-3.5 h-3.5 text-purple-400" /> Desglose por Caída (Match Breakdown)
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                              {row.caidas.map((c, idx) => (
                                <div key={idx} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs flex justify-between items-center">
                                  <div>
                                    <span className="font-bold text-slate-300 block">Caída #{idx + 1}</span>
                                    <span className="text-[10px] text-slate-400">Posición: #{c.pos}</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="font-mono font-bold text-rose-400 text-[11px] block">{c.kills} kills</span>
                                    <span className="font-mono font-extrabold text-amber-300 text-xs">{c.pts} pts</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
