'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api } from '@/lib/api';
import { ApiPerfilEquipo, ApiRecord } from '@/lib/api-types';
import {
  Shield, Trophy, Loader2, Crown, Users, Calendar, ArrowLeft, Award, Swords,
} from 'lucide-react';

const ESTADO_LABEL: Record<string, string> = {
  borrador: 'Borrador',
  inscripciones_abiertas: 'Inscripciones abiertas',
  inscripciones_cerradas: 'Inscripciones cerradas',
  en_curso: 'En curso',
  finalizada: 'Finalizado',
  cancelada: 'Cancelado',
};

function Stat({ valor, etiqueta, color = 'text-white' }: {
  valor: React.ReactNode; etiqueta: string; color?: string;
}) {
  return (
    <div className="text-center">
      <span className={`font-mono text-2xl sm:text-3xl font-black block ${color}`}>{valor}</span>
      <span className="text-[10px] text-tinta-3 uppercase tracking-wider font-semibold">{etiqueta}</span>
    </div>
  );
}

/** "—" y no "0%" cuando todavía no jugó: son cosas distintas. */
function porcentaje(record: ApiRecord): string {
  return record.porcentaje_victorias === null ? '—' : `${record.porcentaje_victorias}%`;
}

export default function PerfilEquipoPage() {
  const params = useParams<{ id: string }>();
  const [perfil, setPerfil] = useState<ApiPerfilEquipo | null>(null);
  const [loading, setLoading] = useState(true);
  const [noExiste, setNoExiste] = useState(false);

  useEffect(() => {
    let activo = true;
    api.getPerfilEquipo(params.id)
      .then(p => activo && setPerfil(p))
      .catch(() => activo && setNoExiste(true))
      .finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, [params.id]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col bg-fondo text-tinta">
        <Navbar />
        <main className="flex-1 flex items-center justify-center gap-2 text-tinta-3 text-sm">
          <Loader2 className="animate-spin" size={18} /> Cargando perfil...
        </main>
        <Footer />
      </div>
    );
  }

  if (noExiste || !perfil) {
    return (
      <div className="min-h-screen flex flex-col bg-fondo text-tinta">
        <Navbar />
        <main className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4 py-24">
          <Shield className="w-10 h-10 text-tinta-4" />
          <h1 className="text-xl font-bold text-white">Este equipo no existe</h1>
          <Link href="/equipos" className="text-xs text-acento-claro hover:text-acento-claro font-semibold">
            Ver todos los equipos
          </Link>
        </main>
        <Footer />
      </div>
    );
  }

  const r = perfil.record_global;

  return (
    <div className="min-h-screen flex flex-col bg-fondo text-tinta selection:bg-acento selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
        <Link href="/equipos" className="inline-flex items-center gap-1.5 text-xs text-tinta-3 hover:text-white transition-colors">
          <ArrowLeft size={13} /> Todos los equipos
        </Link>

        {/* IDENTIDAD + RÉCORD ACUMULADO */}
        <section className="bg-superficie border border-borde rounded-[8px] p-6 sm:p-8 shadow-2xl space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-[6px] bg-acento flex items-center justify-center font-black text-white text-xl shrink-0">
              {perfil.tag || perfil.nombre.slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-black text-white truncate">{perfil.nombre}</h1>
              <div className="flex items-center gap-2.5 text-xs text-tinta-3 mt-0.5">
                {perfil.tag && <span className="font-mono">[{perfil.tag}]</span>}
                <span className="flex items-center gap-1">
                  <Calendar size={11} /> Desde {new Date(perfil.created_at).toLocaleDateString('es-BO')}
                </span>
              </div>
            </div>
            {perfil.titulos > 0 && (
              <span className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-atencion/15 border border-atencion/40 text-atencion text-xs font-black shrink-0">
                <Trophy size={13} /> {perfil.titulos} {perfil.titulos === 1 ? 'título' : 'títulos'}
              </span>
            )}
          </div>

          <div className="grid grid-cols-3 sm:grid-cols-5 gap-4 pt-5 border-t border-borde">
            <Stat valor={perfil.torneos_jugados} etiqueta="Torneos" />
            <Stat valor={r.jugadas} etiqueta="Partidas" />
            <Stat valor={r.ganadas} etiqueta="Ganadas" color="text-ok" />
            <Stat valor={r.perdidas} etiqueta="Perdidas" color="text-vivo" />
            <Stat valor={porcentaje(r)} etiqueta="Victorias" color="text-acento-claro" />
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[11px] text-tinta-3 pt-1">
            <span>
              Mapas <span className="font-mono text-tinta-2">{r.mapas_favor}–{r.mapas_contra}</span>
              <span className={`ml-1.5 font-mono font-bold ${r.diferencia_mapas >= 0 ? 'text-ok' : 'text-vivo'}`}>
                ({r.diferencia_mapas >= 0 ? '+' : ''}{r.diferencia_mapas})
              </span>
            </span>
            {r.byes > 0 && (
              <span title="Un bye es un lugar libre en el cuadro: nadie juega, así que no cuenta como partida ni como victoria.">
                {r.byes} {r.byes === 1 ? 'bye' : 'byes'} (no cuentan en el récord)
              </span>
            )}
          </div>
        </section>

        {/* HISTORIAL TORNEO POR TORNEO */}
        <section className="space-y-3">
          <h2 className="text-sm font-bold text-tinta-2 uppercase tracking-wider flex items-center gap-2">
            <Swords size={15} className="text-tinta-2" /> Historial de torneos
          </h2>

          {perfil.historial.length === 0 ? (
            <div className="glass-card p-10 text-center text-sm text-tinta-3">
              Este equipo todavía no fue aprobado en ningún torneo.
            </div>
          ) : (
            perfil.historial.map((h) => (
              <div key={h.edicion_id} className="glass-card p-5 space-y-3.5">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs text-acento-claro font-semibold">{h.torneo_nombre}</span>
                      <span className="text-tinta-4">•</span>
                      <span className="text-xs text-tinta-3">{h.juego_nombre}</span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-white/5 border border-borde text-tinta-3">
                        {ESTADO_LABEL[h.estado_edicion] || h.estado_edicion}
                      </span>
                    </div>
                    <Link href={`/torneos/${h.edicion_slug}`} className="text-base font-bold text-white hover:text-acento-claro transition-colors">
                      {h.edicion_nombre}
                    </Link>
                  </div>

                  {h.campeon && (
                    <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-atencion/15 border border-atencion/40 text-atencion text-xs font-black shrink-0">
                      <Award size={12} /> CAMPEÓN
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                  <span className="font-mono font-bold text-white">
                    {h.record.ganadas}<span className="text-tinta-4">–</span>{h.record.perdidas}
                  </span>
                  <span className="text-tinta-3">
                    {h.record.jugadas} {h.record.jugadas === 1 ? 'partida' : 'partidas'}
                  </span>
                  <span className="text-tinta-3">
                    Mapas <span className="font-mono">{h.record.mapas_favor}–{h.record.mapas_contra}</span>
                  </span>
                  {h.ronda_maxima !== null && (
                    <span className="text-tinta-3">Llegó a ronda {h.ronda_maxima}</span>
                  )}
                </div>

                {h.roster.length > 0 && (
                  <div className="pt-3 border-t border-borde-sutil">
                    <p className="text-[11px] text-tinta-4 mb-2 flex items-center gap-1.5">
                      <Users size={11} /> Roster de esta edición
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {h.roster.map((j, i) => (
                        <span
                          key={`${j.nick}-${i}`}
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-[4px] text-[11px] border ${
                            j.es_suplente
                              ? 'bg-white/[0.03] border-borde text-tinta-3'
                              : 'bg-white/5 border-borde text-tinta-2'
                          }`}
                        >
                          {j.es_capitan && <Crown size={10} className="text-atencion" />}
                          {j.nick}
                          {j.es_suplente && <span className="text-tinta-4">supl.</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </section>
      </main>

      <Footer />
    </div>
  );
}
