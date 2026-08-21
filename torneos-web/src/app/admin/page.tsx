'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Trophy, Users, ShieldAlert, ClipboardList, Plus,
  Calendar, ArrowRight, Flame, Loader2
} from 'lucide-react';
import { api } from '@/lib/api';
import { ApiDisputa, ApiEdicion, ApiTorneo } from '@/lib/api-types';

function StatCard({
  icon, label, value, sub, color, href
}: {
  icon: React.ReactNode; label: string; value: string | number;
  sub?: string; color: string; href?: string;
}) {
  const content = (
    <div className={`group relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#13131f] to-[#0e0e1a] border border-white/8 p-6 transition-all duration-300 hover:border-white/20 ${href ? 'cursor-pointer' : ''}`}>
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-br ${color} opacity-5`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">{label}</p>
          <p className="text-3xl font-bold text-white mb-1">{value}</p>
          {sub && <p className="text-xs text-white/40">{sub}</p>}
        </div>
        <div className={`p-3 rounded-xl bg-gradient-to-br ${color}`}>{icon}</div>
      </div>
      {href && (
        <div className="mt-4 flex items-center gap-1 text-xs text-white/40 group-hover:text-white/70 transition-colors">
          <span>Ver detalle</span>
          <ArrowRight size={12} />
        </div>
      )}
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : <div>{content}</div>;
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
      <div className="p-6 lg:p-8 max-w-7xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando dashboard...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-white/40 mt-1">Resumen de actividad de tus torneos</p>
        </div>
        <Link
          href="/admin/torneos/nuevo"
          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-violet-500/20"
        >
          <Plus size={16} /> Crear Torneo
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Trophy size={20} className="text-white" />} label="Torneos" value={torneos.length} sub={`${ediciones.length} ediciones en total`} color="from-violet-600 to-violet-800" href="/admin/torneos" />
        <StatCard icon={<Flame size={20} className="text-white" />} label="Ediciones en Curso" value={edicionesEnCurso.length} sub="con inscripciones o partidas activas" color="from-amber-600 to-orange-700" />
        <StatCard icon={<ClipboardList size={20} className="text-white" />} label="Inscripciones Pendientes" value={pendientesPorEdicion} sub="esperan aprobación" color="from-cyan-600 to-blue-700" href="/admin/inscripciones" />
        <StatCard icon={<ShieldAlert size={20} className="text-white" />} label="Disputas Abiertas" value={disputasAbiertas.length} sub="requieren resolución" color="from-red-600 to-red-800" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#13131f] border border-white/8 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-white">Mis Torneos</h2>
              <Link href="/admin/torneos" className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1">
                Ver todos <ArrowRight size={12} />
              </Link>
            </div>
            <div className="space-y-3">
              {torneos.length === 0 && (
                <p className="text-sm text-white/30 text-center py-6">Todavía no creaste ningún torneo.</p>
              )}
              {torneos.map((torneo) => {
                const edicionesDelTorneo = ediciones.filter(e => e.torneo_id === torneo.id);
                return (
                  <Link
                    key={torneo.id}
                    href={`/admin/torneos/${torneo.id}`}
                    className="flex items-center gap-4 p-4 rounded-xl bg-white/5 hover:bg-white/8 border border-white/5 hover:border-white/15 transition-all group"
                  >
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-600 flex items-center justify-center flex-shrink-0 font-black text-white text-sm">
                      {torneo.nombre.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{torneo.nombre}</p>
                      <p className="text-xs text-white/40">{edicionesDelTorneo.length} edición(es)</p>
                    </div>
                    <ArrowRight size={14} className="text-white/20 group-hover:text-white/60 transition-colors" />
                  </Link>
                );
              })}
              <Link
                href="/admin/torneos/nuevo"
                className="flex items-center justify-center gap-2 p-4 rounded-xl border border-dashed border-white/15 hover:border-violet-500/50 text-white/30 hover:text-violet-400 transition-all text-sm"
              >
                <Plus size={16} /> Crear nuevo torneo
              </Link>
            </div>
          </div>

          <div className="bg-[#13131f] border border-white/8 rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-5">Ediciones en Curso</h2>
            <div className="space-y-3">
              {edicionesEnCurso.length === 0 && (
                <p className="text-sm text-white/30 text-center py-6">No hay ediciones activas ahora mismo.</p>
              )}
              {edicionesEnCurso.map((ed) => (
                <div key={ed.id} className="flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/5">
                  <div className={`w-2 h-12 rounded-full flex-shrink-0 ${ed.estado === 'en_curso' ? 'bg-amber-500' : 'bg-cyan-500'}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{ed.nombre}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs text-white/40 flex items-center gap-1">
                        <Users size={11} /> {ed.equipos_aprobados}{ed.max_equipos ? `/${ed.max_equipos}` : ''} equipos
                      </span>
                      {ed.fecha_inicio && (
                        <span className="text-xs text-white/40 flex items-center gap-1">
                          <Calendar size={11} /> {new Date(ed.fecha_inicio).toLocaleDateString('es', { day: 'numeric', month: 'short' })}
                        </span>
                      )}
                    </div>
                  </div>
                  <Link
                    href={`/admin/torneos/${ed.torneo_id}/ediciones/${ed.id}/participantes`}
                    className="px-3 py-1.5 text-xs bg-violet-600/30 hover:bg-violet-600/60 text-violet-300 rounded-lg transition-all"
                  >
                    Gestionar
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-[#13131f] border border-white/8 rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-4">Acciones Rápidas</h2>
            <div className="space-y-2">
              <Link href="/admin/inscripciones" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/8 hover:bg-cyan-500/10 hover:border-cyan-500/30 transition-all">
                <span className="text-white/50"><ClipboardList size={15} /></span>
                <span className="text-sm text-white/70 flex-1">Aprobar inscripciones</span>
                {pendientesPorEdicion > 0 && (
                  <span className="bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">{pendientesPorEdicion}</span>
                )}
              </Link>
              <Link href="/admin/torneos/nuevo" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/8 hover:bg-violet-500/10 hover:border-violet-500/30 transition-all">
                <span className="text-white/50"><Plus size={15} /></span>
                <span className="text-sm text-white/70 flex-1">Crear nuevo torneo</span>
              </Link>
            </div>
          </div>

          <div className="bg-[#13131f] border border-white/8 rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <ShieldAlert size={15} className="text-red-400" /> Disputas Abiertas
            </h2>
            <div className="space-y-3">
              {disputasAbiertas.length === 0 && (
                <p className="text-xs text-white/30">No hay disputas pendientes.</p>
              )}
              {disputasAbiertas.slice(0, 5).map((d) => (
                <div key={d.id} className="text-xs text-white/60 border-l-2 border-red-500/40 pl-3 py-0.5">
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
