'use client';

/**
 * Staff de un torneo — quién más ayuda a correrlo sin ser organizador
 * global. Hasta ahora esto solo se podía tocar pegándole a la API a mano
 * (ver [torneos.py](../../../../../../../torneos-backend/app/api/routes/torneos.py)):
 * esta pantalla es la puerta de entrada real.
 *
 * Sumar y sacar staff es del organizador global — igual que en el backend
 * (`RequiereOrganizador` en las tres rutas de /staff), a propósito: si un
 * administrador de torneo pudiera repartir el propio acceso, alcanzaría
 * con delegar una vez para perder el control de lo delegado.
 */

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft, UserPlus, Search, Loader2, AlertTriangle,
  Shield, Gavel, X, Crown,
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiStaff, ApiTorneo, ApiUsuarioBusqueda, RolStaff } from '@/lib/api-types';

const ROL_INFO: Record<RolStaff, { label: string; desc: string; icon: React.ReactNode; color: string }> = {
  administrador: {
    label: 'Administrador',
    desc: 'Arma el torneo: inscripciones, sorteo, sanciones. Todo lo que hace un árbitro también.',
    icon: <Shield size={13} />,
    color: 'bg-acento/15 text-acento-claro border-borde',
  },
  arbitro: {
    label: 'Árbitro',
    desc: 'El día de partido: programar, check-in, disputas, corregir resultados.',
    icon: <Gavel size={13} />,
    color: 'bg-elevada text-tinta-2 border-borde',
  },
};

export default function StaffDeTorneoPage() {
  const params = useParams();
  const torneoId = params.id as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [staff, setStaff] = useState<ApiStaff[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [buscando, setBuscando] = useState(false);
  const [query, setQuery] = useState('');
  const [resultados, setResultados] = useState<ApiUsuarioBusqueda[]>([]);
  const [rolElegido, setRolElegido] = useState<RolStaff>('arbitro');
  const [agregandoId, setAgregandoId] = useState<number | null>(null);
  const [quitandoId, setQuitandoId] = useState<number | null>(null);

  const cargar = () => {
    Promise.all([api.getTorneoById(torneoId), api.getStaffDeTorneo(torneoId)])
      .then(([t, s]) => { setTorneo(t); setStaff(s); })
      .catch(() => setError('No se pudo cargar el staff de este torneo.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { cargar(); }, [torneoId]);

  // Buscar con un pequeño debounce: no hace falta pegarle a la API en
  // cada tecla, y evita que una respuesta vieja pise a una más nueva. El
  // "buscando" se prende recién cuando el debounce vence y arranca el
  // pedido — no de entrada en el efecto — porque poner estado ahí mismo
  // dispara un render en cascada.
  useEffect(() => {
    let vigente = true;
    const t = setTimeout(() => {
      if (!vigente) return;
      setBuscando(true);
      api.buscarUsuarios(query)
        .then(r => { if (vigente) setResultados(r); })
        .catch(() => { if (vigente) setResultados([]); })
        .finally(() => { if (vigente) setBuscando(false); });
    }, 250);
    return () => { vigente = false; clearTimeout(t); };
  }, [query]);

  const yaEsStaff = (usuarioId: number) => staff.some(s => s.usuario_id === usuarioId);

  const handleAgregar = async (usuario: ApiUsuarioBusqueda) => {
    setError(null);
    setAgregandoId(usuario.id);
    try {
      await api.agregarStaff(torneoId, usuario.id, rolElegido);
      cargar();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar a esa persona.');
    } finally {
      setAgregandoId(null);
    }
  };

  const handleQuitar = async (usuarioId: number) => {
    setError(null);
    setQuitandoId(usuarioId);
    try {
      await api.quitarStaff(torneoId, usuarioId);
      setStaff(prev => prev.filter(s => s.usuario_id !== usuarioId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo quitar a esa persona.');
    } finally {
      setQuitandoId(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-3xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando staff...
      </div>
    );
  }

  if (!torneo) {
    return (
      <div className="p-6 lg:p-8 max-w-3xl mx-auto text-center py-24 text-tinta-3">
        Este torneo no existe.
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto">
      <Link
        href={`/admin/torneos/${torneoId}`}
        className="inline-flex items-center gap-2 text-sm text-tinta-3 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={16} /> {torneo.nombre}
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <UserPlus size={22} className="text-acento-claro" /> Staff de {torneo.nombre}
        </h1>
        <p className="text-sm text-tinta-3 mt-1">
          Dale a alguien acceso a este torneo puntual, sin hacerlo organizador de toda la plataforma.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
          <AlertTriangle size={15} /> <span>{error}</span>
        </div>
      )}

      {/* Buscador para sumar staff */}
      <div className="glass-card p-5 mb-6">
        <h2 className="text-sm font-bold text-white mb-3">Agregar a alguien</h2>

        <div className="flex gap-2 mb-3">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-tinta-4" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar por nombre de Discord..."
              className="w-full bg-white/5 border border-borde text-white rounded-[6px] pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-acento"
            />
          </div>
          <select
            value={rolElegido}
            onChange={(e) => setRolElegido(e.target.value as RolStaff)}
            className="bg-white/5 border border-borde text-tinta-2 text-xs rounded-[6px] px-3 py-2.5 focus:outline-none focus:border-acento"
          >
            {(Object.keys(ROL_INFO) as RolStaff[]).map(r => (
              <option key={r} value={r} className="bg-superficie text-white">{ROL_INFO[r].label}</option>
            ))}
          </select>
        </div>

        <p className="text-xs text-tinta-4 mb-3">{ROL_INFO[rolElegido].desc}</p>

        <div className="space-y-1.5 min-h-[3rem]">
          {buscando && (
            <div className="flex items-center gap-2 text-tinta-4 text-xs py-2">
              <Loader2 size={13} className="animate-spin" /> Buscando...
            </div>
          )}
          {!buscando && resultados.length === 0 && (
            <p className="text-xs text-white/25 py-2">
              {query.trim() ? 'Nadie coincide con esa búsqueda.' : 'Sin resultados.'}
            </p>
          )}
          {!buscando && resultados.map(u => {
            const yaAsignado = yaEsStaff(u.id);
            return (
              <div
                key={u.id}
                className="flex items-center justify-between gap-3 p-2.5 bg-white/5 rounded-[6px] border border-borde-sutil"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {u.discord_avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={u.discord_avatar_url} alt="" className="w-7 h-7 rounded-full flex-shrink-0" />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-white/10 flex-shrink-0" />
                  )}
                  <span className="text-sm text-tinta-2 truncate">{u.discord_username}</span>
                  {u.es_organizador && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-atencion/15 text-atencion border border-atencion/30 flex-shrink-0">
                      <Crown size={10} /> Organizador global
                    </span>
                  )}
                </div>
                {u.es_organizador ? (
                  <span className="text-xs text-white/25 flex-shrink-0 pr-1">Ya entra a todos los torneos</span>
                ) : yaAsignado ? (
                  <span className="text-xs text-white/25 flex-shrink-0 pr-1">Ya es staff</span>
                ) : (
                  <button
                    onClick={() => handleAgregar(u)}
                    disabled={agregandoId === u.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-acento hover:bg-acento disabled:opacity-50 text-white text-xs font-semibold rounded-[4px] transition-all flex-shrink-0"
                  >
                    {agregandoId === u.id ? <Loader2 size={12} className="animate-spin" /> : <UserPlus size={12} />}
                    Agregar
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Staff actual */}
      <div className="glass-card p-5">
        <h2 className="text-sm font-bold text-white mb-3">Staff actual</h2>

        {staff.length === 0 && (
          <p className="text-sm text-tinta-4 py-6 text-center">
            Nadie más tiene acceso a este torneo todavía.
          </p>
        )}

        <div className="space-y-1.5">
          {staff.map(s => {
            const info = ROL_INFO[s.rol];
            return (
              <div
                key={s.id}
                className="flex items-center justify-between gap-3 p-2.5 bg-white/5 rounded-[6px] border border-borde-sutil"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {s.usuario_avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={s.usuario_avatar_url} alt="" className="w-7 h-7 rounded-full flex-shrink-0" />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-white/10 flex-shrink-0" />
                  )}
                  <span className="text-sm text-tinta-2 truncate">{s.usuario_nombre}</span>
                  <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border flex-shrink-0 ${info.color}`}>
                    {info.icon} {info.label}
                  </span>
                </div>
                <button
                  onClick={() => handleQuitar(s.usuario_id)}
                  disabled={quitandoId === s.usuario_id}
                  title="Quitarle el acceso a este torneo"
                  className="flex items-center gap-1 px-2.5 py-1.5 text-tinta-3 hover:text-vivo hover:bg-rose-500/10 disabled:opacity-50 text-xs rounded-[4px] transition-all flex-shrink-0"
                >
                  {quitandoId === s.usuario_id ? <Loader2 size={12} className="animate-spin" /> : <X size={12} />}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
