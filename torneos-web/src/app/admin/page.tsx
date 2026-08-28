'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Trophy, Users, ShieldAlert, ClipboardList, Plus,
  Calendar, ArrowRight, Flame, Loader2
} from 'lucide-react';
import { api } from '@/lib/api';
import { ApiDisputa, ApiEdicion, ApiTorneo } from '@/lib/api-types';

/**
 * Tarjeta de cifra del panel.
 *
 * `color` ya no pinta un gradiente de fondo: marca el estado de la cifra.
 * En un tablero de control, un número teñido tiene que querer decir algo —
 * si todos son de colores distintos porque quedaba lindo, ninguno avisa
 * nada. Solo lo que pide acción se destaca; el resto es neutro.
 */
function StatCard({
  icon, label, value, sub, tono = 'neutro', href
}: {
  icon: React.ReactNode; label: string; value: string | number;
  sub?: string; tono?: 'neutro' | 'atencion' | 'vivo'; href?: string;
}) {
  const borde = tono === 'atencion' ? 'estado-atencion' : tono === 'vivo' ? 'estado-vivo' : '';
  const cifra = tono === 'atencion' ? 'text-atencion' : tono === 'vivo' ? 'text-vivo' : 'text-tinta';

  const content = (
    <div className={`group h-full glass-card ${borde} p-5 transition-colors hover:border-borde-fuerte ${href ? 'cursor-pointer' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold text-tinta-3 uppercase tracking-[0.08em] mb-2.5">{label}</p>
          <p className={`font-mono tabular text-[30px] font-semibold leading-none ${cifra}`}>{value}</p>
          {sub && <p className="text-[12px] text-tinta-3 mt-2">{sub}</p>}
        </div>
        <div className="text-tinta-4 shrink-0">{icon}</div>
      </div>
      {href && (
        <div className="mt-4 flex items-center gap-1 text-[12px] text-tinta-3 group-hover:text-tinta-2 transition-colors">
          <span>Ver detalle</span>
          <ArrowRight size={12} />
        </div>
      )}
    </div>
  );
  return href ? <Link href={href} className="block h-full">{content}</Link> : <div>{content}</div>;
}

export default function AdminDashboard() {
  const [torneos, setTorneos] = useState<ApiTorneo[]>([]);
  const [ediciones, setEdiciones] = useState<ApiEdicion[]>([]);
  const [pendientesPorEdicion, setPendientesPorEdicion] = useState<number>(0);
  const [disputas, setDisputas] = useState<ApiDisputa[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let activo = true;
    Promise.all([
      api.getTorneos(),
      api.getEdiciones(),
      api.getDisputasGlobal().catch(() => []),
    ]).then(async ([t, eds, disp]) => {
      if (!activo) return;
      setTorneos(t.map(x => ({ id: Number(x.id), nombre: x.nombre, slug: x.slug, descripcion: null, logo_url: null })));
      setEdiciones(eds);
      setDisputas(disp);

      const pendientesPorEd = await Promise.all(
        eds.map(e => api.getInscripciones(String(e.id), 'pendiente').then(l => l.length).catch(() => 0))
      );
      if (activo) setPendientesPorEdicion(pendientesPorEd.reduce((a, b) => a + b, 0));
    }).finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, []);

  const disputasAbiertas = disputas.filter(d => d.estado === 'abierta' || d.estado === 'en_revision');
  const edicionesEnCurso = ediciones.filter(e => e.estado === 'en_curso' || e.estado === 'inscripciones_abiertas');

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando dashboard...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-tinta-3 mt-1">Resumen de actividad de tus torneos</p>
        </div>
        <Link
          href="/admin/torneos/nuevo"
          className="flex items-center gap-2 px-4 py-2.5 bg-acento text-white text-sm font-semibold rounded-[6px] transition-all"
        >
          <Plus size={16} /> Crear Torneo
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Solo se tiñe lo que pide que hagas algo: inscripciones esperando
            y disputas abiertas. Y solo cuando hay más de cero — un "0
            disputas" en rojo enseña a ignorar el rojo. */}
        <StatCard icon={<Trophy size={18} />} label="Torneos" value={torneos.length} sub={`${ediciones.length} ediciones en total`} href="/admin/torneos" />
        <StatCard icon={<Flame size={18} />} label="Ediciones en curso" value={edicionesEnCurso.length} sub="con inscripciones o partidas activas" />
        <StatCard icon={<ClipboardList size={18} />} label="Inscripciones pendientes" value={pendientesPorEdicion} sub="esperan aprobación" tono={pendientesPorEdicion > 0 ? 'atencion' : 'neutro'} href="/admin/inscripciones" />
        <StatCard icon={<ShieldAlert size={18} />} label="Disputas abiertas" value={disputasAbiertas.length} sub="requieren resolución" tono={disputasAbiertas.length > 0 ? 'vivo' : 'neutro'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-white">Mis Torneos</h2>
              <Link href="/admin/torneos" className="text-xs text-acento-claro hover:text-acento-claro flex items-center gap-1">
                Ver todos <ArrowRight size={12} />
              </Link>
            </div>
            <div className="space-y-3">
              {torneos.length === 0 && (
                <p className="text-sm text-tinta-4 text-center py-6">Todavía no creaste ningún torneo.</p>
              )}
              {torneos.map((torneo) => {
                const edicionesDelTorneo = ediciones.filter(e => e.torneo_id === torneo.id);
                return (
                  <Link
                    key={torneo.id}
                    href={`/admin/torneos/${torneo.id}`}
                    className="flex items-center gap-4 p-4 rounded-[6px] bg-white/5 hover:bg-white/8 border border-borde-sutil hover:border-borde-fuerte transition-all group"
                  >
                    <div className="w-10 h-10 rounded-[6px] bg-acento flex items-center justify-center flex-shrink-0 font-black text-white text-sm">
                      {torneo.nombre.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{torneo.nombre}</p>
                      <p className="text-xs text-tinta-3">{edicionesDelTorneo.length} edición(es)</p>
                    </div>
                    <ArrowRight size={14} className="text-tinta-4 group-hover:text-tinta-2 transition-colors" />
                  </Link>
                );
              })}
              <Link
                href="/admin/torneos/nuevo"
                className="flex items-center justify-center gap-2 p-4 rounded-[6px] border border-dashed border-borde-fuerte hover:border-acento/50 text-tinta-4 hover:text-acento-claro transition-all text-sm"
              >
                <Plus size={16} /> Crear nuevo torneo
              </Link>
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-base font-bold text-white mb-5">Ediciones en Curso</h2>
            <div className="space-y-3">
              {edicionesEnCurso.length === 0 && (
                <p className="text-sm text-tinta-4 text-center py-6">No hay ediciones activas ahora mismo.</p>
              )}
              {edicionesEnCurso.map((ed) => (
                <div key={ed.id} className="flex items-center gap-4 p-4 rounded-[6px] bg-white/5 border border-borde-sutil">
                  <div className={`w-2 h-12 rounded-full flex-shrink-0 ${ed.estado === 'en_curso' ? 'bg-amber-500' : 'bg-acento'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{ed.nombre}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs text-tinta-3 flex items-center gap-1">
                        <Users size={11} /> {ed.equipos_aprobados}{ed.max_equipos ? `/${ed.max_equipos}` : ''} equipos
                      </span>
                      {ed.fecha_inicio && (
                        <span className="text-xs text-tinta-3 flex items-center gap-1">
                          <Calendar size={11} /> {new Date(ed.fecha_inicio).toLocaleDateString('es', { day: 'numeric', month: 'short' })}
                        </span>
                      )}
                    </div>
                  </div>
                  <Link
                    href={`/admin/torneos/${ed.torneo_id}/ediciones/${ed.id}/participantes`}
                    className="px-3 py-1.5 text-xs bg-acento/30 hover:bg-acento/60 text-acento-claro rounded-[4px] transition-all"
                  >
                    Gestionar
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="glass-card p-6">
            <h2 className="text-base font-bold text-white mb-4">Acciones Rápidas</h2>
            <div className="space-y-2">
              <Link href="/admin/inscripciones" className="flex items-center gap-3 p-3 rounded-[6px] bg-white/5 border border-borde hover:bg-elevada hover:border-borde transition-all">
                <span className="text-tinta-3"><ClipboardList size={15} /></span>
                <span className="text-sm text-tinta-2 flex-1">Aprobar inscripciones</span>
                {pendientesPorEdicion > 0 && (
                  <span className="bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">{pendientesPorEdicion}</span>
                )}
              </Link>
              <Link href="/admin/torneos/nuevo" className="flex items-center gap-3 p-3 rounded-[6px] bg-white/5 border border-borde hover:bg-acento/10 hover:border-borde transition-all">
                <span className="text-tinta-3"><Plus size={15} /></span>
                <span className="text-sm text-tinta-2 flex-1">Crear nuevo torneo</span>
              </Link>
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <ShieldAlert size={15} className="text-vivo" /> Disputas Abiertas
            </h2>
            <div className="space-y-3">
              {disputasAbiertas.length === 0 && (
                <p className="text-xs text-tinta-4">No hay disputas pendientes.</p>
              )}
              {disputasAbiertas.slice(0, 5).map((d) => (
                <div key={d.id} className="text-xs text-tinta-2 border-l-2 border-red-500/40 pl-3 py-0.5">
                  Partida #{d.partida_id} — {d.motivo}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
