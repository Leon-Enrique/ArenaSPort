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
      <div className="p-6 lg:p-8 max-w-6xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando torneos...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Mis Torneos</h1>
          <p className="text-sm text-tinta-3 mt-1">{torneos.length} torneos en total</p>
        </div>
        <Link
          href="/admin/torneos/nuevo"
          className="flex items-center gap-2 px-4 py-2.5 bg-acento text-white text-sm font-semibold rounded-[6px] transition-all"
        >
          <Plus size={16} /> Nuevo Torneo
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {torneos.map((torneo) => {
          const edicionesDelTorneo = ediciones.filter(e => e.torneo_id === torneo.id);
          const activo = edicionesDelTorneo.some(e => e.estado === 'en_curso' || e.estado === 'inscripciones_abiertas');
          return (
            <div key={torneo.id} className="group glass-card overflow-hidden hover:border-white/20 transition-all">
              <div className="relative h-24 bg-acento flex items-center justify-center">
                <span className="text-3xl font-black text-tinta-4">{torneo.nombre.slice(0, 2).toUpperCase()}</span>
                <div className="absolute inset-0 bg-superficie/80" />
                <div className="absolute top-3 right-3">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                    activo ? 'bg-green-500/20 text-ok border-green-500/30' : 'bg-gray-500/20 text-gray-400 border-gray-500/30'
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
                  <p className="text-xs text-tinta-3 leading-relaxed mb-4 line-clamp-2">{torneo.descripcion}</p>
                )}

                <div className="flex items-center gap-2 text-xs text-tinta-3 mb-5">
                  <Trophy size={12} className="text-acento-claro" />
                  <span>{edicionesDelTorneo.length} edición(es)</span>
                </div>

                <div className="flex gap-2">
                  <Link
                    href={`/admin/torneos/${torneo.id}`}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-acento/20 hover:bg-acento/40 border border-borde text-acento-claro text-xs font-semibold rounded-[6px] transition-all"
                  >
                    <Edit2 size={13} /> Gestionar
                  </Link>
                  <Link
                    href={`/torneos/${torneo.slug}`}
                    className="flex items-center justify-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-white/10 border border-borde text-tinta-3 hover:text-white text-xs rounded-[6px] transition-all"
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
          className="flex flex-col items-center justify-center gap-3 p-8 bg-superficie border-2 border-dashed border-borde rounded-[6px] hover:border-borde hover:bg-acento/5 text-tinta-4 hover:text-acento-claro transition-all group"
        >
          <div className="w-12 h-12 rounded-[6px] bg-white/5 group-hover:bg-acento/20 flex items-center justify-center transition-all">
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
