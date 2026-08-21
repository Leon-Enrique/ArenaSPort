'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Trophy, Calendar, Edit2, Eye, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { ApiEdicion, ApiTorneo } from '@/lib/api-types';

export default function TorneosAdminPage() {
  const [torneos, setTorneos] = useState<ApiTorneo[]>([]);
  const [ediciones, setEdiciones] = useState<ApiEdicion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let activo = true;
    Promise.all([api.getTorneos(), api.getEdiciones()])
      .then(([t, eds]) => {
        if (!activo) return;
        setTorneos(t.map(x => ({ id: Number(x.id), nombre: x.nombre, slug: x.slug, descripcion: null, logo_url: null })));
        setEdiciones(eds);
      })
      .finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, []);

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-white/40 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando torneos...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Mis Torneos</h1>
          <p className="text-sm text-white/40 mt-1">{torneos.length} torneos en total</p>
        </div>
        <Link
          href="/admin/torneos/nuevo"
          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-violet-500 hover:from-violet-500 hover:to-violet-400 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-violet-500/20"
        >
          <Plus size={16} /> Nuevo Torneo
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {torneos.map((torneo) => {
          const edicionesDelTorneo = ediciones.filter(e => e.torneo_id === torneo.id);
          const activo = edicionesDelTorneo.some(e => e.estado === 'en_curso' || e.estado === 'inscripciones_abiertas');
          return (
            <div key={torneo.id} className="group bg-[#13131f] border border-white/8 rounded-2xl overflow-hidden hover:border-white/20 transition-all">
              <div className="relative h-24 bg-gradient-to-r from-violet-600 to-cyan-600 flex items-center justify-center">
                <span className="text-3xl font-black text-white/20">{torneo.nombre.slice(0, 2).toUpperCase()}</span>
                <div className="absolute inset-0 bg-gradient-to-t from-[#13131f] to-transparent" />
                <div className="absolute top-3 right-3">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                    activo ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-gray-500/20 text-gray-400 border-gray-500/30'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${activo ? 'bg-green-400' : 'bg-gray-500'}`} />
                    {activo ? 'Activo' : 'Sin ediciones activas'}
                  </span>
                </div>
              </div>

              <div className="p-5 -mt-2">
                <div className="flex items-start justify-between mb-3">
                  <h2 className="text-base font-bold text-white">{torneo.nombre}</h2>
                </div>

                {torneo.descripcion && (
                  <p className="text-xs text-white/50 leading-relaxed mb-4 line-clamp-2">{torneo.descripcion}</p>
                )}

                <div className="flex items-center gap-2 text-xs text-white/40 mb-5">
                  <Trophy size={12} className="text-violet-400" />
                  <span>{edicionesDelTorneo.length} edición(es)</span>
                </div>

                <div className="flex gap-2">
                  <Link
                    href={`/admin/torneos/${torneo.id}`}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-violet-600/20 hover:bg-violet-600/40 border border-violet-500/30 text-violet-300 text-xs font-semibold rounded-xl transition-all"
                  >
                    <Edit2 size={13} /> Gestionar
                  </Link>
                  <Link
                    href={`/torneos/${torneo.slug}`}
                    className="flex items-center justify-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white/50 hover:text-white text-xs rounded-xl transition-all"
                  >
                    <Eye size={13} /> Ver público
                  </Link>
                </div>
              </div>
            </div>
          );
        })}

        <Link
          href="/admin/torneos/nuevo"
          className="flex flex-col items-center justify-center gap-3 p-8 bg-[#13131f] border-2 border-dashed border-white/10 rounded-2xl hover:border-violet-500/40 hover:bg-violet-500/5 text-white/30 hover:text-violet-400 transition-all group"
        >
          <div className="w-12 h-12 rounded-2xl bg-white/5 group-hover:bg-violet-500/20 flex items-center justify-center transition-all">
            <Plus size={24} />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold">Crear nuevo torneo</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
