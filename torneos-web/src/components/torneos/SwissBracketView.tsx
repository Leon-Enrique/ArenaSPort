'use client';

import React from 'react';
import { Partida } from '@/types';
import { Trophy, XCircle, Crown, Skull } from 'lucide-react';

interface Props {
  partidas: Partida[];
  onSelectPartida?: (partida: Partida) => void;
  metaVictorias?: number;
  metaDerrotas?: number;
}

interface Bucket {
  label: string;
  wins: number;
  losses: number;
  partidas: Partida[];
}

interface RoundColumn {
  ronda: number;
  buckets: Bucket[];
}

const RESUELTOS = new Set(['confirmada', 'walkover', 'bye']);

function construirColumnas(partidas: Partida[]) {
  const porRonda = new Map<number, Partida[]>();
  partidas.forEach(p => {
    const r = p.numeroRonda || 1;
    if (!porRonda.has(r)) porRonda.set(r, []);
    porRonda.get(r)!.push(p);
  });

  const rondas = Array.from(porRonda.keys()).sort((a, b) => a - b);
  const record = new Map<string, { w: number; l: number }>();
  const nombrePorEquipo = new Map<string, string>();
  const columnas: RoundColumn[] = [];

  for (const ronda of rondas) {
    const partidasRonda = porRonda.get(ronda)!;
    const buckets = new Map<string, Bucket>();

    for (const p of partidasRonda) {
      p.participaciones.forEach(part => {
        if (part.equipoId && part.equipo?.nombre) nombrePorEquipo.set(part.equipoId, part.equipo.nombre);
      });
      const eqA = p.participaciones[0];
      const rec = eqA?.equipoId ? (record.get(eqA.equipoId) || { w: 0, l: 0 }) : { w: 0, l: 0 };
      const label = `${rec.w}-${rec.l}`;
      if (!buckets.has(label)) buckets.set(label, { label, wins: rec.w, losses: rec.l, partidas: [] });
      buckets.get(label)!.partidas.push(p);
    }

    columnas.push({
      ronda,
      buckets: Array.from(buckets.values()).sort((a, b) => (b.wins - a.wins) || (a.losses - b.losses)),
    });

    for (const p of partidasRonda) {
      if (!RESUELTOS.has(p.estado)) continue;
      for (const part of p.participaciones) {
        if (!part.equipoId) continue;
        const rec = record.get(part.equipoId) || { w: 0, l: 0 };
        if (part.esGanador) rec.w += 1;
        else if (p.participaciones.length === 2) rec.l += 1;
        record.set(part.equipoId, rec);
      }
    }
  }

  return { columnas, record, nombrePorEquipo };
}

function MatchCard({ partida, onClick }: { partida: Partida; onClick?: () => void }) {
  const [a, b] = partida.participaciones;
  return (
    <div
      onClick={onClick}
      className="w-[210px] rounded-[6px] overflow-hidden border border-borde bg-superficie hover:border-acento transition-all cursor-pointer shrink-0"
    >
      {[a, b].map((p, idx) => (
        <div
          key={idx}
          className={`px-2.5 h-[30px] flex items-center justify-between text-xs ${idx === 0 ? 'border-b border-borde-sutil' : ''} ${p?.esGanador ? 'bg-elevada' : ''}`}
        >
          <span className={`truncate max-w-[150px] text-[11px] ${p?.esGanador ? 'text-white font-black' : p?.equipo ? 'text-tinta-2 font-medium' : 'text-tinta-4 italic'}`}>
            {p?.equipo?.nombre || 'Por definir'}
          </span>
          <span className={`font-mono text-xs font-bold px-1.5 rounded min-w-[18px] text-center ${p?.esGanador ? 'bg-ok text-fondo' : 'text-tinta-4 bg-superficie/60'}`}>
            {p?.mapasGanados ?? '—'}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SwissBracketView({ partidas, onSelectPartida, metaVictorias = 3, metaDerrotas = 3 }: Props) {
  const { columnas, record, nombrePorEquipo } = construirColumnas(partidas);

  if (columnas.length === 0) {
    return (
      <div className="bg-hundida border border-borde rounded-[6px] p-10 text-center text-xs text-tinta-3">
        Todavía no hay rondas sorteadas para esta fase.
      </div>
    );
  }

  const clasificados = Array.from(record.entries()).filter(([, r]) => r.w >= metaVictorias);
  const eliminados = Array.from(record.entries()).filter(([, r]) => r.l >= metaDerrotas);
  const todosResueltos = clasificados.length + eliminados.length >= record.size && record.size > 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-[11px] text-tinta-3 bg-hundida border border-borde rounded-[6px] px-4 py-2.5 w-fit">
        <Trophy size={13} className="text-ok" /> Clasifica con {metaVictorias} victorias
        <span className="text-slate-700">•</span>
        <XCircle size={13} className="text-vivo" /> Elimina con {metaDerrotas} derrotas
      </div>

      {todosResueltos && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-[6px] border border-ok/30 bg-ok/10 p-4 space-y-2">
            <span className="text-xs font-black uppercase text-ok flex items-center gap-1.5">
              <Crown size={13} /> Clasificados ({clasificados.length})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {clasificados.map(([id, r]) => (
                <span key={id} className="px-2 py-1 rounded-[4px] bg-ok/15 border border-ok/25 text-[11px] text-ok font-semibold">
                  {nombrePorEquipo.get(id) || id} <span className="text-ok/60 font-mono">{r.w}-{r.l}</span>
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-[6px] border border-rose-500/30 bg-rose-950/20 p-4 space-y-2">
            <span className="text-xs font-black uppercase text-vivo flex items-center gap-1.5">
              <Skull size={13} /> Eliminados ({eliminados.length})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {eliminados.map(([id, r]) => (
                <span key={id} className="px-2 py-1 rounded-[4px] bg-rose-500/10 border border-rose-500/20 text-[11px] text-rose-200 font-semibold">
                  {nombrePorEquipo.get(id) || id} <span className="text-vivo/60 font-mono">{r.w}-{r.l}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="flex items-start gap-6 overflow-x-auto pb-4">
        {columnas.map((col) => (
          <div key={col.ronda} className="shrink-0 space-y-3">
            <div className="text-center">
              <span className="text-[11px] font-black uppercase tracking-wider text-acento-claro font-mono">
                Ronda {col.ronda}
              </span>
            </div>
            <div className="space-y-4">
              {col.buckets.map((bucket) => (
                <div key={bucket.label} className="rounded-[6px] border border-borde bg-fondo/40 p-3 space-y-2">
                  <div className="flex justify-center">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black font-mono bg-elevada/80 border border-borde text-tinta-2">
                      {bucket.label}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {bucket.partidas.map((p) => (
                      <MatchCard key={p.id} partida={p} onClick={() => onSelectPartida?.(p)} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
