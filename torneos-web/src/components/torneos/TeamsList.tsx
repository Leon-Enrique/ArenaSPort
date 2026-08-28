'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Users, Shield, Crown, Search, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { ApiInscripcion } from '@/lib/api-types';

interface TeamsListProps {
  edicionId: string;
  maxEquipos: number | null;
  equiposCount: number;
}

export default function TeamsList({ edicionId, maxEquipos, equiposCount }: TeamsListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [inscripciones, setInscripciones] = useState<ApiInscripcion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let activo = true;
    setLoading(true);
    api.getInscripcionesAprobadas(edicionId)
      .then(data => activo && setInscripciones(data))
      .catch(() => activo && setInscripciones([]))
      .finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, [edicionId]);

  const filtered = useMemo(
    () => inscripciones.filter(i => i.equipo.nombre.toLowerCase().includes(searchTerm.toLowerCase())),
    [inscripciones, searchTerm]
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h3 className="text-sm font-black text-white flex items-center gap-2">
          <Users size={16} className="text-tinta-2" />
          Equipos Inscritos ({equiposCount}{maxEquipos ? ` / ${maxEquipos}` : ''})
        </h3>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-tinta-4" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Buscar equipo..."
            className="pl-8 pr-3 py-2 bg-[#0e101d] border border-borde rounded-[6px] text-xs text-white focus:outline-none focus:border-borde-fuerte w-full sm:w-56"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center gap-2 text-tinta-3 text-xs py-16">
          <Loader2 className="animate-spin" size={16} /> Cargando equipos...
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[#0e101d] border border-borde rounded-[6px] p-10 text-center text-xs text-tinta-3">
          {inscripciones.length === 0 ? 'Todavía no hay equipos aprobados en este torneo.' : 'Ningún equipo coincide con la búsqueda.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(insc => {
            const capitan = insc.jugadores.find(j => j.es_capitan);
            return (
              <Link
                key={insc.id}
                href={`/equipos/${insc.equipo.id}`}
                className="block bg-[#0e101d] border border-borde rounded-[6px] p-4 space-y-3 hover:border-borde transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-[6px] bg-acento flex items-center justify-center font-black text-white text-sm shrink-0">
                    {insc.equipo.tag || insc.equipo.nombre.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="font-bold text-sm text-white truncate group-hover:text-tinta-2 transition-colors">
                      {insc.equipo.nombre}
                    </p>
                    {capitan && (
                      <span className="text-[11px] text-tinta-3 flex items-center gap-1 truncate">
                        <Crown size={10} className="text-atencion shrink-0" /> {capitan.identidad.nick || capitan.identidad.nombre || 'Capitán'}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center justify-between text-[11px] text-tinta-3">
                  <span className="flex items-center gap-1.5">
                    <Shield size={11} /> {insc.jugadores.length} jugadores registrados
                  </span>
                  <span className="text-tinta-2/0 group-hover:text-tinta-2/70 transition-colors">Ver perfil →</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
