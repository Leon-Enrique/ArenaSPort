'use client';

import React from 'react';
import { Trophy, Shield, Loader2 } from 'lucide-react';
import { ApiTablaGrupo } from '@/lib/api-types';

interface GroupStageViewProps {
  grupos: ApiTablaGrupo[];
  clasificadosPorGrupo?: number;
  loading?: boolean;
}

export default function GroupStageView({ grupos, clasificadosPorGrupo = 1, loading }: GroupStageViewProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 text-white/40 text-xs py-16">
        <Loader2 className="animate-spin" size={16} /> Cargando tabla de posiciones...
      </div>
    );
  }

  if (grupos.length === 0) {
    return (
      <div className="bg-[#0e101d] border border-slate-800 rounded-2xl p-10 text-center text-xs text-white/40">
        Todavía no hay resultados cargados para esta fase.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {grupos.map((grupo) => (
        <div key={grupo.grupo ?? 'general'} className="bg-[#0e101d] rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-800 flex items-center gap-2 bg-slate-950/60">
            <Shield size={15} className="text-purple-400" />
            <span className="text-sm font-black text-white">
              {grupo.grupo != null ? `Grupo ${grupo.grupo}` : 'Tabla General'}
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-white/40 border-b border-slate-800/80">
                  <th className="text-left font-semibold px-4 py-2">#</th>
                  <th className="text-left font-semibold px-2 py-2">Equipo</th>
                  <th className="text-center font-semibold px-2 py-2">PJ</th>
                  <th className="text-center font-semibold px-2 py-2">V</th>
                  <th className="text-center font-semibold px-2 py-2">E</th>
                  <th className="text-center font-semibold px-2 py-2">D</th>
                  <th className="text-center font-semibold px-2 py-2">Dif</th>
                  <th className="text-center font-semibold px-4 py-2">Pts</th>
                </tr>
              </thead>
              <tbody>
                {grupo.filas.map((fila) => (
                  <tr
                    key={fila.equipo_id}
                    className={`border-b border-slate-900 last:border-0 ${
                      fila.posicion <= clasificadosPorGrupo ? 'bg-emerald-950/20' : ''
                    }`}
                  >
                    <td className="px-4 py-2.5 font-mono text-white/50">{fila.posicion}</td>
                    <td className="px-2 py-2.5 font-bold text-white flex items-center gap-1.5">
                      {fila.posicion <= clasificadosPorGrupo && <Trophy size={11} className="text-emerald-400 shrink-0" />}
                      {fila.equipo_nombre}
                    </td>
                    <td className="text-center px-2 py-2.5 text-white/70">{fila.jugados}</td>
                    <td className="text-center px-2 py-2.5 text-emerald-400 font-bold">{fila.victorias}</td>
                    <td className="text-center px-2 py-2.5 text-white/50">{fila.empates}</td>
                    <td className="text-center px-2 py-2.5 text-rose-400/80">{fila.derrotas}</td>
                    <td className="text-center px-2 py-2.5 font-mono text-white/60">
                      {fila.diferencia_mapas > 0 ? `+${fila.diferencia_mapas}` : fila.diferencia_mapas}
                    </td>
                    <td className="text-center px-4 py-2.5 font-mono font-black text-amber-400">{fila.puntos}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
