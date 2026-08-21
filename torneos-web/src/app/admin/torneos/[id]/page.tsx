'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft, Users, Swords, ShieldAlert, Trophy, Plus,
  Settings, Eye, Loader2, AlertTriangle, Trash2
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiEdicion, ApiTorneo } from '@/lib/api-types';

const ESTADOS_DISPONIBLES = [
  { value: 'borrador', label: 'Borrador' },
  { value: 'inscripciones_abiertas', label: 'Inscripciones Abiertas' },
  { value: 'inscripciones_cerradas', label: 'Inscripciones Cerradas' },
  { value: 'en_curso', label: 'En Curso' },
  { value: 'finalizada', label: 'Finalizada (cerrar torneo)' },
  { value: 'cancelada', label: 'Cancelada' },
];

const ESTADO_CONFIG: Record<string, { label: string; color: string }> = {
  borrador: { label: 'Borrador', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
  inscripciones_abiertas: { label: 'Inscripciones Abiertas', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
  inscripciones_cerradas: { label: 'Inscripciones Cerradas', color: 'bg-slate-500/20 text-slate-300 border-slate-500/30' },
  en_curso: { label: 'En Curso', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  finalizada: { label: 'Finalizada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  cancelada: { label: 'Cancelada', color: 'bg-rose-500/20 text-rose-400 border-rose-500/30' },
};

export default function TorneoDetailPage() {
  const params = useParams();
  const router = useRouter();
  const torneoId = params.id as string;
  const [activeTab, setActiveTab] = useState<'ediciones' | 'config'>('ediciones');
  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [ediciones, setEdiciones] = useState<ApiEdicion[]>([]);
  const [loading, setLoading] = useState(true);
  const [cambiandoEstado, setCambiandoEstado] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cargar = () => {
    Promise.all([api.getTorneoById(torneoId), api.getEdicionesByTorneo(torneoId)])
      .then(([t, eds]) => { setTorneo(t); setEdiciones(eds); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [torneoId]);

  const [confirmarNombre, setConfirmarNombre] = useState('');
  const [eliminando, setEliminando] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleEliminarTorneo = async () => {
    if (!torneo || confirmarNombre !== torneo.nombre) return;
    setDeleteError(null);
    setEliminando(true);
    try {
      await api.deleteTorneo(torneoId);
      router.push('/admin/torneos');
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'No se pudo eliminar el torneo.');
      setEliminando(false);
    }
  };

  const handleCambiarEstado = async (edicionId: number, estado: string) => {
    setError(null);
    setCambiandoEstado(edicionId);
    try {
      await api.cambiarEstadoEdicion(String(edicionId), estado);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar el estado.');
    } finally {
      setCambiandoEstado(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando torneo...
      </div>
    );
  }

  if (!torneo) {
    return (
      <div className="p-6 lg:p-8 max-w-5xl mx-auto text-center py-24 text-white/40">
        Este torneo no existe.
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <Link href="/admin/torneos" className="inline-flex items-center gap-2 text-sm text-white/40 hover:text-white mb-6 transition-colors">
        <ArrowLeft size={16} /> Mis torneos
      </Link>

      <div className="relative rounded-2xl overflow-hidden mb-6 h-36 bg-gradient-to-r from-violet-700 to-cyan-700">
        <div className="absolute inset-0 bg-gradient-to-r from-[#08080f]/90 to-[#08080f]/40" />
        <div className="relative p-6 h-full flex flex-col justify-end">
          <div className="flex items-end justify-between flex-wrap gap-3">
            <div>
              <h1 className="text-2xl font-bold text-white">{torneo.nombre}</h1>
              <span className="text-xs text-white/40">{ediciones.length} edición(es)</span>
            </div>
            <div className="flex gap-2">
              {ediciones[0] && (
                <Link
                  href={`/torneos/${ediciones[0].slug}`}
                  className="flex items-center gap-1.5 px-3 py-2 bg-white/10 hover:bg-white/20 text-white text-xs rounded-xl border border-white/20 transition-all"
                >
                  <Eye size={13} /> Vista pública
                </Link>
              )}
              <Link
                href={`/admin/torneos/${torneoId}/ediciones/nueva`}
                className="flex items-center gap-1.5 px-3 py-2 bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold rounded-xl transition-all"
              >
                <Plus size={13} /> Nueva edición
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-1 mb-6 bg-white/5 p-1 rounded-xl w-fit">
        {([
          { id: 'ediciones', label: 'Ediciones', icon: <Trophy size={14} /> },
          { id: 'config', label: 'Configuración', icon: <Settings size={14} /> },
        ] as const).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.id ? 'bg-violet-600 text-white' : 'text-white/50 hover:text-white'}`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle size={15} /> <span>{error}</span>
        </div>
      )}

      {activeTab === 'ediciones' && (
        <div className="space-y-4">
          {ediciones.length === 0 && (
            <div className="text-center py-16 text-white/30">
              <Trophy size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No hay ediciones. Crea la primera.</p>
            </div>
          )}

          {ediciones.map((ed) => {
            const conf = ESTADO_CONFIG[ed.estado] ?? ESTADO_CONFIG['borrador'];
            return (
              <div key={ed.id} className="bg-[#13131f] border border-white/8 rounded-2xl p-5 hover:border-white/15 transition-all">
                <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold text-white/30 uppercase">Edición #{ed.numero}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${conf.color}`}>{conf.label}</span>
                    </div>
                    <h3 className="text-base font-bold text-white">{ed.nombre}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    {ed.bolsa_premios && <div className="text-sm font-bold text-amber-400">{ed.bolsa_premios}</div>}
                    <select
                      value={ed.estado}
                      disabled={cambiandoEstado === ed.id}
                      onChange={(e) => handleCambiarEstado(ed.id, e.target.value)}
                      title="Cambiar el estado de esta edición — usá 'Finalizada' para cerrar el torneo."
                      className="bg-white/5 border border-white/10 text-white/70 text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:border-violet-500 disabled:opacity-50"
                    >
                      {ESTADOS_DISPONIBLES.map(o => (
                        <option key={o.value} value={o.value} className="bg-[#13131f] text-white">{o.label}</option>
                      ))}
                    </select>
                    {cambiandoEstado === ed.id && <Loader2 size={14} className="animate-spin text-white/40" />}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="text-center p-3 bg-white/5 rounded-xl">
                    <p className="text-lg font-bold text-white">{ed.equipos_aprobados}</p>
                    <p className="text-xs text-white/40">{ed.max_equipos ? `/ ${ed.max_equipos} equipos` : 'equipos aprobados'}</p>
                  </div>
                  <div className="text-center p-3 bg-white/5 rounded-xl">
                    <p className="text-sm font-bold text-white">
                      {ed.fecha_inicio ? new Date(ed.fecha_inicio).toLocaleDateString('es', { day: 'numeric', month: 'short' }) : '—'}
                    </p>
                    <p className="text-xs text-white/40">Inicio</p>
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap">
                  {[
                    { href: `/admin/torneos/${torneoId}/ediciones/${ed.id}/participantes`, label: 'Participantes', icon: <Users size={12} /> },
                    { href: `/admin/torneos/${torneoId}/ediciones/${ed.id}/fases`, label: 'Fases', icon: <Swords size={12} /> },
                    { href: `/admin/torneos/${torneoId}/ediciones/${ed.id}/disputas`, label: 'Disputas', icon: <ShieldAlert size={12} /> },
                    { href: `/admin/torneos/${torneoId}/ediciones/${ed.id}/configuracion`, label: 'Configuración', icon: <Settings size={12} /> },
                  ].map(link => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/25 text-white/60 hover:text-white text-xs rounded-xl transition-all"
                    >
                      {link.icon} {link.label}
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}

          <Link
            href={`/admin/torneos/${torneoId}/ediciones/nueva`}
            className="flex items-center justify-center gap-2 p-5 bg-[#13131f] border-2 border-dashed border-white/10 rounded-2xl hover:border-violet-500/40 text-white/30 hover:text-violet-400 transition-all text-sm"
          >
            <Plus size={16} /> Crear nueva edición
          </Link>
        </div>
      )}

      {activeTab === 'config' && (
        <div className="bg-[#13131f] border border-white/8 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-bold text-white">Configuración del torneo</h2>
          <div>
            <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">Nombre</label>
            <div className="w-full bg-white/5 border border-white/10 text-white rounded-xl px-4 py-3 text-sm">{torneo.nombre}</div>
          </div>
          {torneo.descripcion && (
            <div>
              <label className="block text-xs font-semibold text-white/40 uppercase tracking-wider mb-2">Descripción</label>
              <div className="w-full bg-white/5 border border-white/10 text-white/80 rounded-xl px-4 py-3 text-sm">{torneo.descripcion}</div>
            </div>
          )}
          <p className="text-xs text-white/30">Editar estos datos todavía no está disponible.</p>
        </div>
      )}

      {activeTab === 'config' && (
        <div className="mt-4 bg-rose-950/10 border border-rose-500/20 rounded-2xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertTriangle size={16} />
            <h2 className="text-base font-bold">Zona de Peligro</h2>
          </div>
          <p className="text-xs text-white/50">
            Borra el torneo completo — todas sus ediciones, fases, inscripciones y partidas. Solo funciona si
            ninguna partida tuvo actividad real todavía (sin check-ins, reportes ni resultados). Los equipos
            en sí no se borran, siguen existiendo para otros torneos. <strong className="text-rose-300">Esta acción no se puede deshacer.</strong>
          </p>
          {deleteError && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle size={15} /> <span>{deleteError}</span>
            </div>
          )}
          <div>
            <label className="block text-xs font-semibold text-white/40 mb-2">
              Escribí <span className="text-white font-mono">{torneo.nombre}</span> para confirmar
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={confirmarNombre}
                onChange={(e) => setConfirmarNombre(e.target.value)}
                placeholder={torneo.nombre}
                className="flex-1 bg-white/5 border border-white/10 text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-rose-500"
              />
              <button
                type="button"
                onClick={handleEliminarTorneo}
                disabled={confirmarNombre !== torneo.nombre || eliminando}
                className="flex items-center gap-2 px-4 py-2.5 bg-rose-600 hover:bg-rose-500 disabled:bg-white/5 disabled:text-white/20 text-white text-xs font-bold rounded-xl transition-all disabled:cursor-not-allowed"
              >
                {eliminando ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                Eliminar Torneo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
