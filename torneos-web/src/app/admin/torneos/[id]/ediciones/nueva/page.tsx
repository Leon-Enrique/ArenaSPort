'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft, Calendar, Layers, Save, AlertCircle, Loader2, Gamepad2
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiTorneo } from '@/lib/api-types';
import { Juego } from '@/types';

export default function NuevaEdicionPage() {
  const params = useParams();
  const router = useRouter();
  const torneoId = params.id as string;

  const [torneo, setTorneo] = useState<ApiTorneo | null>(null);
  const [juegos, setJuegos] = useState<Juego[]>([]);
  const [juegoId, setJuegoId] = useState<string>('');
  const [siguienteNumero, setSiguienteNumero] = useState(1);
  const [loadingInicial, setLoadingInicial] = useState(true);

  useEffect(() => {
    Promise.all([api.getTorneoById(torneoId), api.getJuegos(), api.getEdicionesByTorneo(torneoId)])
      .then(([t, js, eds]) => {
        setTorneo(t);
        setJuegos(js);
        if (js[0]) setJuegoId(js[0].id);
        setSiguienteNumero(eds.length + 1);
      })
      .finally(() => setLoadingInicial(false));
  }, [torneoId]);

  const [nombre, setNombre] = useState('');
  const [bolsaPremios, setBolsaPremios] = useState('');
  const [maxEquipos, setMaxEquipos] = useState(16);
  const [fechaInicio, setFechaInicio] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!juegoId) {
      setError('Elegí un juego.');
      return;
    }
    setLoading(true);
    try {
      await api.createEdicion({
        torneo_id: Number(torneoId),
        juego_id: Number(juegoId),
        numero: siguienteNumero,
        nombre: nombre.trim(),
        max_equipos: maxEquipos,
        fecha_inicio: fechaInicio || undefined,
        bolsa_premios: bolsaPremios || undefined,
      });
      router.push(`/admin/torneos/${torneoId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo crear la edición.');
      setLoading(false);
    }
  };

  if (loadingInicial) {
    return (
      <div className="p-6 lg:p-8 max-w-3xl mx-auto flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={18} /> Cargando...
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-2 text-xs text-tinta-4">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">{torneo?.nombre}</Link>
        <span>/</span>
        <span className="text-tinta-2">Nueva Edición</span>
      </div>

      <div>
        <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
          <Layers className="text-tinta-2" /> Crear Nueva Edición
        </h1>
        <p className="text-sm text-tinta-3 mt-1">
          Edición #{siguienteNumero} de {torneo?.nombre}.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-superficie border border-borde rounded-[6px] p-6 space-y-6 shadow-xl">
        <div>
          <label className="block text-xs font-semibold text-tinta-2 mb-1.5 flex items-center gap-1.5">
            <Gamepad2 size={13} className="text-acento-claro" /> Juego
          </label>
          <select
            value={juegoId}
            onChange={(e) => setJuegoId(e.target.value)}
            className="w-full bg-fondo border border-borde rounded-[6px] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500"
          >
            {juegos.map(j => <option key={j.id} value={j.id}>{j.nombre}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Nombre de la Edición</label>
          <input
            type="text" required value={nombre} onChange={(e) => setNombre(e.target.value)}
            placeholder="Ej. Season 3 - Gran Final de Apertura"
            className="w-full bg-fondo border border-borde rounded-[6px] px-4 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Bolsa de Premios (opcional)</label>
            <input
              type="text" value={bolsaPremios} onChange={(e) => setBolsaPremios(e.target.value)}
              placeholder="Ej. $1,500 USD"
              className="w-full bg-fondo border border-borde rounded-[6px] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500 font-mono font-bold"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Capacidad Máxima (Equipos)</label>
            <input
              type="number" min={2} max={256} value={maxEquipos}
              onChange={(e) => setMaxEquipos(Number(e.target.value))}
              className="w-full bg-fondo border border-borde rounded-[6px] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500 font-mono font-bold"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-tinta-2 mb-1.5 flex items-center gap-1.5">
            <Calendar size={13} className="text-tinta-2" /> Fecha de Inicio (opcional)
          </label>
          <input
            type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)}
            className="w-full bg-fondo border border-borde rounded-[6px] px-3 py-2.5 text-sm text-white focus:outline-none focus:border-cyan-500 font-mono"
          />
        </div>

        {error && (
          <div className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
            <AlertCircle size={15} /> <span>{error}</span>
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-borde-sutil">
          <Link href={`/admin/torneos/${torneoId}`} className="px-4 py-2.5 bg-white/5 hover:bg-white/10 text-tinta-2 hover:text-white rounded-[6px] text-xs font-semibold">
            Cancelar
          </Link>
          <button
            type="submit" disabled={loading}
            className="flex items-center gap-2 px-6 py-2.5 bg-acento hover:from-cyan-500 hover:to-violet-500 text-white text-sm font-bold rounded-[6px] transition-all disabled:opacity-50"
          >
            {loading ? <span>Creando...</span> : <><Save size={16} /> Publicar Nueva Edición</>}
          </button>
        </div>
      </form>
    </div>
  );
}
