'use client';

/**
 * Tu ID de juego, en tu cuenta.
 *
 * Es la pieza de la que cuelga todo lo demás: sin esto cargado no te pueden
 * inscribir en ningún torneo. Por eso cuando falta no se muestra como un
 * campo más del perfil sino como una tarea pendiente, con el estado bien
 * arriba y el motivo escrito.
 *
 * Lo carga cada uno para sí mismo, nunca el capitán. La razón no es de
 * privacidad: el nick que ponés acá es el que ve tu RIVAL para encontrarte
 * y jugar la partida, así que un dato mal copiado por un tercero no es un
 * detalle feo, es una partida que no se juega. Battlefy llegó a lo mismo.
 */

import React, { useEffect, useState } from 'react';
import {
  AlertTriangle, CheckCircle2, Gamepad2, Loader2, Pencil, ShieldCheck, X,
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiIdentidadDeJuego, ApiJuego } from '@/lib/api-types';

interface Props {
  /** Se avisa hacia arriba porque de esto depende poder inscribirse. */
  onCambio?: (identidad: ApiIdentidadDeJuego | null) => void;
}

export default function IdentidadDeJuegoPanel({ onCambio }: Props) {
  const [juego, setJuego] = useState<ApiJuego | null>(null);
  const [identidad, setIdentidad] = useState<ApiIdentidadDeJuego | null>(null);
  const [cargando, setCargando] = useState(true);
  const [editando, setEditando] = useState(false);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recienGuardado, setRecienGuardado] = useState(false);

  useEffect(() => {
    let vivo = true;
    Promise.all([api.getJuegosCrudos(), api.getMisIdentidades()])
      .then(([juegos, identidades]) => {
        if (!vivo) return;
        const activo = juegos[0] ?? null;
        setJuego(activo);
        const mia = activo
          ? identidades.find((i) => i.juego_id === activo.id) ?? null
          : null;
        setIdentidad(mia);
        setValores(mia?.identidad ?? {});
        onCambio?.(mia);
      })
      .catch(() => { /* el panel se muestra vacío y deja cargar igual */ })
      .finally(() => vivo && setCargando(false));
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const campos = juego?.campos_identidad.campos ?? [];

  const guardar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!juego) return;
    setGuardando(true);
    setError(null);
    try {
      const guardada = await api.guardarMiIdentidad({
        identidad: valores, juego_id: juego.id,
      });
      setIdentidad(guardada);
      setEditando(false);
      setRecienGuardado(true);
      setTimeout(() => setRecienGuardado(false), 3000);
      onCambio?.(guardada);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo guardar.');
    } finally {
      setGuardando(false);
    }
  };

  if (cargando) {
    return (
      <div className="glass-card rounded-[6px] p-6 flex items-center gap-3 text-tinta-3">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Cargando tu identidad de juego…</span>
      </div>
    );
  }

  if (!juego) return null;

  const falta = !identidad;
  const mostrarForm = editando || falta;

  return (
    <section
      className={`relative overflow-hidden rounded-[6px] border transition-colors ${
        falta
          ? 'border-atencion/40 bg-superficie estado-atencion'
          : 'glass-card'
      }`}
    >
      {/* Halo de color: atención cuando falta algo, elevada cuando está resuelto. */}
      <div
        className={`pointer-events-none absolute -top-24 -right-16 h-48 w-48 rounded-full blur-3xl ${
          falta ? 'bg-atencion/20' : 'bg-elevada'
        }`}
      />

      <div className="relative p-6">
        <header className="flex items-start justify-between gap-4 mb-5">
          <div className="flex items-start gap-3">
            <div
              className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-[6px] ${
                falta
                  ? 'bg-atencion/15 text-atencion'
                  : 'bg-elevada text-tinta-2'
              }`}
            >
              <Gamepad2 size={18} />
            </div>
            <div>
              <h2 className="font-bold tracking-tight text-tinta flex items-center gap-2">
                Tu ID de {juego.nombre}
                {!falta && !recienGuardado && (
                  <ShieldCheck size={14} className="text-tinta-2" />
                )}
              </h2>
              <p className="text-xs text-tinta-3 mt-0.5 max-w-md leading-relaxed">
                Se carga una sola vez y sirve para todos tus torneos. Tu rival
                ve este nick para encontrarte y jugar la partida.
              </p>
            </div>
          </div>

          {!mostrarForm && (
            <button
              onClick={() => { setEditando(true); setValores(identidad?.identidad ?? {}); }}
              className="shrink-0 flex items-center gap-1.5 rounded-[4px] border border-borde px-3 py-1.5 text-xs font-medium text-tinta-2 transition-colors hover:border-borde-fuerte hover:text-tinta"
            >
              <Pencil size={12} /> Corregir
            </button>
          )}
        </header>

        {falta && !editando && (
          <div className="mb-5 flex items-start gap-2.5 rounded-[6px] border border-atencion/25 bg-atencion/10 px-4 py-3">
            <AlertTriangle size={15} className="mt-0.5 shrink-0 text-atencion" />
            <p className="text-[13px] leading-relaxed text-atencion">
              <strong className="font-semibold text-atencion">Falta cargarlo.</strong>{' '}
              Sin esto tu capitán no puede inscribirte en ningún torneo, aunque
              ya estés en el equipo.
            </p>
          </div>
        )}

        {recienGuardado && (
          <div className="mb-5 flex items-center gap-2 rounded-[6px] border border-ok/25 bg-ok/10 px-4 py-3">
            <CheckCircle2 size={15} className="text-tinta-2" />
            <p className="text-[13px] text-ok">
              Guardado. Se actualizó en todos tus equipos.
            </p>
          </div>
        )}

        {mostrarForm ? (
          <form onSubmit={guardar} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              {campos.map((campo) => (
                <label key={campo.nombre} className="block">
                  <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wider text-tinta-3">
                    {campo.etiqueta}
                    {campo.requerido && <span className="ml-1 text-acento-claro">*</span>}
                  </span>
                  <input
                    value={valores[campo.nombre] ?? ''}
                    onChange={(e) =>
                      setValores((v) => ({ ...v, [campo.nombre]: e.target.value }))
                    }
                    required={campo.requerido}
                    autoComplete="off"
                    className="w-full rounded-[4px] border border-borde bg-hundida px-3 py-2 text-sm text-tinta placeholder-tinta-4 outline-none transition-colors focus:border-acento focus:bg-hundida"
                    placeholder={campo.etiqueta}
                  />
                </label>
              ))}
            </div>

            {error && (
              <p className="flex items-start gap-2 rounded-[4px] border border-vivo/30 bg-vivo/10 px-3 py-2 text-[13px] text-vivo">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                {error}
              </p>
            )}

            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={guardando}
                className="inline-flex items-center gap-2 rounded-[4px] bg-acento px-4 py-2 text-sm font-semibold text-tinta  transition-opacity hover:bg-acento-hover disabled:opacity-50"
              >
                {guardando && <Loader2 size={14} className="animate-spin" />}
                {falta ? 'Guardar mi ID' : 'Guardar cambios'}
              </button>
              {!falta && (
                <button
                  type="button"
                  onClick={() => { setEditando(false); setError(null); }}
                  className="inline-flex items-center gap-1.5 rounded-[4px] px-3 py-2 text-sm text-tinta-3 transition-colors hover:text-tinta"
                >
                  <X size={14} /> Cancelar
                </button>
              )}
            </div>
          </form>
        ) : (
          <dl className="grid gap-3 sm:grid-cols-3">
            {campos.map((campo) => (
              <div
                key={campo.nombre}
                className="rounded-[6px] border border-borde bg-hundida px-3.5 py-2.5"
              >
                <dt className="text-[10px] font-semibold uppercase tracking-wider text-tinta-3">
                  {campo.etiqueta}
                </dt>
                <dd className="mt-0.5 truncate font-mono text-sm text-tinta">
                  {identidad?.identidad[campo.nombre] || '—'}
                </dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  );
}
