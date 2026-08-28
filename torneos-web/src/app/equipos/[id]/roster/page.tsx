'use client';

/**
 * El plantel permanente del equipo.
 *
 * La pantalla está construida alrededor de una sola regla:
 *
 *     Entrar no requiere aceptar; salir no requiere permiso.
 *
 * Por eso sumar a alguien es un solo click desde el buscador —armar el
 * equipo no puede depender de que cinco personas contesten un mensaje— y
 * por eso el que está adentro puede irse solo, sin pedirle nada al capitán.
 *
 * El capitán nunca escribe el ID de juego de nadie: sale de la cuenta de
 * cada uno. Cuando falta, la fila lo muestra en ámbar, porque esa persona
 * no puede ser inscrita en un torneo hasta que lo cargue.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  AlertTriangle, ArrowLeft, Check, Copy, Crown, Link2, Loader2, LogOut,
  Search, ShieldAlert, UserMinus, UserPlus, Users, X,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api, ApiError } from '@/lib/api';
import { ApiJugadorBuscado, ApiMiembroEquipo, ApiPerfilEquipo } from '@/lib/api-types';
import { Usuario } from '@/types';

const TOKEN_KEY = 'torneos_auth_token';

export default function RosterPage() {
  const params = useParams();
  const equipoId = Number(params.id);

  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [equipo, setEquipo] = useState<ApiPerfilEquipo | null>(null);
  const [miembros, setMiembros] = useState<ApiMiembroEquipo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);

  const recargar = useCallback(async () => {
    setMiembros(await api.getMiembrosEquipo(equipoId));
  }, [equipoId]);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) api.setToken(token);

    Promise.all([
      token ? api.getMe().catch(() => null) : Promise.resolve(null),
      api.getPerfilEquipo(equipoId).catch(() => null),
      api.getMiembrosEquipo(equipoId),
    ])
      .then(([me, perfil, lista]) => {
        setUsuario(me);
        setEquipo(perfil);
        setMiembros(lista);
      })
      .catch((err) => {
        setErrorCarga(
          err instanceof ApiError && err.status === 403
            ? 'Este equipo no es tuyo. Solo su dueño puede ver el plantel.'
            : 'No se pudo cargar el plantel.',
        );
      })
      .finally(() => setCargando(false));
  }, [equipoId]);

  const sinIdentidad = miembros.filter((m) => !m.identidad);

  if (cargando) {
    return (
      <Pantalla>
        <div className="flex items-center justify-center gap-3 py-32 text-tinta-3">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">Cargando el plantel…</span>
        </div>
      </Pantalla>
    );
  }

  if (errorCarga) {
    return (
      <Pantalla>
        <div className="glass-card mx-auto mt-20 max-w-md rounded-[6px] p-8 text-center">
          <ShieldAlert size={28} className="mx-auto mb-3 text-tinta-4" />
          <p className="text-sm text-tinta-2">{errorCarga}</p>
          <Link
            href="/perfil"
            className="mt-5 inline-flex items-center gap-1.5 text-xs font-medium text-acento-claro hover:text-acento"
          >
            <ArrowLeft size={13} /> Volver a mi perfil
          </Link>
        </div>
      </Pantalla>
    );
  }

  return (
    <Pantalla>
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <Link
          href="/perfil"
          className="mb-6 inline-flex items-center gap-1.5 text-xs font-medium text-tinta-3 transition-colors hover:text-tinta"
        >
          <ArrowLeft size={13} /> Mi perfil
        </Link>

        <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-acento-claro">
              Plantel permanente
            </p>
            <h1 className="text-3xl font-extrabold tracking-tight text-tinta">
              {equipo?.nombre ?? 'Mi equipo'}
            </h1>
            <p className="mt-1.5 max-w-lg text-sm leading-relaxed text-tinta-3">
              Esta gente se inscribe con vos en cada torneo, sin volver a cargar
              sus datos.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-[6px] border border-borde bg-hundida px-4 py-2.5">
            <Users size={15} className="text-tinta-2" />
            <span className="text-2xl font-bold leading-none text-tinta">
              {miembros.length}
            </span>
            <span className="text-xs text-tinta-3">jugadores</span>
          </div>
        </header>

        {sinIdentidad.length > 0 && (
          <div className="mb-6 flex items-start gap-3 rounded-[6px] border border-atencion/25 bg-atencion/10 px-5 py-4">
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-atencion" />
            <div className="text-[13px] leading-relaxed text-atencion">
              <strong className="font-semibold text-atencion">
                {sinIdentidad.length === 1
                  ? '1 jugador todavía no cargó su ID de juego'
                  : `${sinIdentidad.length} jugadores todavía no cargaron su ID de juego`}
                .
              </strong>{' '}
              No los vas a poder inscribir hasta que lo hagan, y solo ellos
              pueden cargarlo. Ya les llegó el aviso.
            </div>
          </div>
        )}

        <BuscadorDeJugadores
          equipoId={equipoId}
          yaEstan={miembros.map((m) => m.usuario_id)}
          onAgregado={recargar}
        />

        <ListaDeMiembros
          equipoId={equipoId}
          miembros={miembros}
          usuarioActualId={usuario?.id ? Number(usuario.id) : null}
          duenioId={equipo?.propietario_usuario_id ?? null}
          onCambio={recargar}
        />

        <InvitacionPorLink equipoId={equipoId} />
      </div>
    </Pantalla>
  );
}

function Pantalla({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}

/* ── Sumar gente ─────────────────────────────────────────────────────── */

function BuscadorDeJugadores({
  equipoId, yaEstan, onAgregado,
}: {
  equipoId: number;
  yaEstan: number[];
  onAgregado: () => Promise<void>;
}) {
  const [q, setQ] = useState('');
  const [resultados, setResultados] = useState<ApiJugadorBuscado[]>([]);
  const [buscando, setBuscando] = useState(false);
  const [agregando, setAgregando] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Con el campo vacío no se limpia el estado: se deja de mostrar. Vaciar
  // `resultados` desde el efecto es un setState sincrónico que dispara un
  // render en cascada — y no hace falta, porque lo que se ve es derivado.
  const visibles = q.trim() ? resultados : [];

  useEffect(() => {
    if (debounce.current) clearTimeout(debounce.current);
    if (!q.trim()) return;

    // El spinner se enciende dentro del timeout y no en el cuerpo del
    // efecto: además de evitar el setState sincrónico, deja de parpadear
    // en cada tecla mientras alguien escribe rápido.
    debounce.current = setTimeout(() => {
      setBuscando(true);
      api.buscarJugadores(q)
        .then(setResultados)
        .catch(() => setResultados([]))
        .finally(() => setBuscando(false));
    }, 250);

    return () => { if (debounce.current) clearTimeout(debounce.current); };
  }, [q]);

  const agregar = async (jugador: ApiJugadorBuscado) => {
    setAgregando(jugador.usuario_id);
    setError(null);
    try {
      await api.agregarMiembro(equipoId, jugador.usuario_id);
      await onAgregado();
      setQ('');
      setResultados([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo agregar.');
    } finally {
      setAgregando(null);
    }
  };

  return (
    <section className="glass-card mb-6 rounded-[6px] p-5">
      <div className="mb-3 flex items-center gap-2">
        <UserPlus size={15} className="text-acento-claro" />
        <h2 className="text-sm font-bold text-tinta">Sumar un jugador</h2>
      </div>

      <div className="relative">
        <Search
          size={15}
          className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-tinta-4"
        />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscá por nick del juego o nombre de cuenta…"
          className="w-full rounded-[6px] border border-borde bg-hundida py-3 pl-10 pr-10 text-sm text-tinta placeholder-tinta-4 outline-none transition-colors focus:border-acento focus:bg-hundida"
        />
        {buscando && (
          <Loader2
            size={14}
            className="absolute right-3.5 top-1/2 -translate-y-1/2 animate-spin text-tinta-4"
          />
        )}
      </div>

      <p className="mt-2 text-[11px] leading-relaxed text-tinta-4">
        Entra directo, sin tener que aceptar — le llega un aviso y puede
        salirse solo cuando quiera.
      </p>

      {error && (
        <p className="mt-3 flex items-start gap-2 rounded-[4px] border border-vivo/30 bg-vivo/10 px-3 py-2 text-[13px] text-vivo">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {error}
        </p>
      )}

      {q.trim() && !buscando && visibles.length === 0 && (
        <p className="mt-4 rounded-[6px] border border-borde bg-hundida px-4 py-3 text-[13px] leading-relaxed text-tinta-3">
          Nadie con ese nombre. Si todavía no tiene cuenta,{' '}
          <span className="text-tinta-2">mandale el link de abajo</span> — se
          registra y queda en el equipo.
        </p>
      )}

      {visibles.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {visibles.map((j) => {
            const adentro = yaEstan.includes(j.usuario_id);
            return (
              <li
                key={j.usuario_id}
                className="flex items-center justify-between gap-3 rounded-[6px] border border-borde bg-hundida px-4 py-2.5"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-tinta">
                    {j.nick ?? j.nombre}
                  </p>
                  {j.nick && (
                    <p className="truncate text-[11px] text-tinta-3">{j.nombre}</p>
                  )}
                </div>
                {adentro ? (
                  <span className="shrink-0 text-[11px] font-medium text-tinta-4">
                    Ya está
                  </span>
                ) : (
                  <button
                    onClick={() => agregar(j)}
                    disabled={agregando === j.usuario_id}
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-[4px] bg-acento px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-acento-hover disabled:opacity-50"
                  >
                    {agregando === j.usuario_id
                      ? <Loader2 size={12} className="animate-spin" />
                      : <UserPlus size={12} />}
                    Sumar
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/* ── El plantel ──────────────────────────────────────────────────────── */

function ListaDeMiembros({
  equipoId, miembros, usuarioActualId, duenioId, onCambio,
}: {
  equipoId: number;
  miembros: ApiMiembroEquipo[];
  usuarioActualId: number | null;
  duenioId: number | null;
  onCambio: () => Promise<void>;
}) {
  const [sacando, setSacando] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sacar = async (miembro: ApiMiembroEquipo) => {
    setSacando(miembro.id);
    setError(null);
    try {
      await api.sacarDelRoster(equipoId, miembro.id);
      await onCambio();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo.');
    } finally {
      setSacando(null);
    }
  };

  if (miembros.length === 0) {
    return (
      <section className="glass-card mb-6 rounded-[6px] px-6 py-12 text-center">
        <Users size={26} className="mx-auto mb-3 text-tinta-4" />
        <p className="text-sm font-medium text-tinta-2">
          Todavía no hay nadie en el plantel
        </p>
        <p className="mx-auto mt-1.5 max-w-sm text-[13px] leading-relaxed text-tinta-3">
          Buscá a tus jugadores arriba y sumalos. Los que no tengan cuenta
          entran con el link.
        </p>
      </section>
    );
  }

  return (
    <section className="mb-6">
      {error && (
        <p className="mb-3 flex items-start gap-2 rounded-[4px] border border-vivo/30 bg-vivo/10 px-3 py-2 text-[13px] text-vivo">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {error}
        </p>
      )}

      <ul className="space-y-2">
        {miembros.map((m) => {
          const soyYo = usuarioActualId !== null && m.usuario_id === usuarioActualId;
          const esDuenio = duenioId !== null && m.usuario_id === duenioId;
          const falta = !m.identidad;

          return (
            <li
              key={m.id}
              className={`group flex items-center gap-4 rounded-[6px] border px-5 py-3.5 transition-colors ${
                falta
                  ? 'border-atencion/25 bg-atencion/5'
                  : 'border-borde bg-superficie hover:border-borde-fuerte'
              }`}
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[6px] text-sm font-bold ${
                  falta
                    ? 'bg-atencion/15 text-atencion'
                    : 'bg-borde text-tinta-2'
                }`}
              >
                {(m.identidad?.nick ?? m.usuario_nombre ?? '?').charAt(0).toUpperCase()}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate font-semibold text-tinta">
                    {m.identidad?.nick ?? m.usuario_nombre ?? 'Sin nombre'}
                  </p>
                  {esDuenio && (
                    <span
                      title="Dueño del equipo — es el capitán en cada inscripción"
                      className="inline-flex shrink-0 items-center gap-1 rounded-md border border-atencion/30 bg-atencion/10 px-1.5 py-0.5 text-[10px] font-semibold text-atencion"
                    >
                      <Crown size={9} /> Capitán
                    </span>
                  )}
                  {soyYo && (
                    <span className="shrink-0 text-[10px] font-medium text-tinta-4">
                      vos
                    </span>
                  )}
                </div>
                {falta ? (
                  <p className="mt-0.5 text-[11px] text-atencion/80">
                    Le falta cargar su ID — no se lo puede inscribir todavía
                  </p>
                ) : (
                  <p className="mt-0.5 truncate font-mono text-[11px] text-tinta-3">
                    {m.identidad?.id_juego}
                    {m.identidad?.server ? ` · ${m.identidad.server}` : ''}
                  </p>
                )}
              </div>

              <button
                onClick={() => sacar(m)}
                disabled={sacando === m.id}
                title={soyYo ? 'Salir del equipo' : 'Sacar del plantel'}
                className={`inline-flex shrink-0 items-center gap-1.5 rounded-[4px] border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
                  soyYo
                    ? 'border-borde text-tinta-3 hover:border-vivo hover:text-vivo'
                    : 'border-transparent text-tinta-4 hover:border-vivo hover:text-vivo'
                }`}
              >
                {sacando === m.id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : soyYo ? (
                  <LogOut size={12} />
                ) : (
                  <UserMinus size={12} />
                )}
                {soyYo ? 'Salirme' : 'Sacar'}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/* ── El link, para quien todavía no tiene cuenta ─────────────────────── */

function InvitacionPorLink({ equipoId }: { equipoId: number }) {
  const [link, setLink] = useState<string | null>(null);
  const [generando, setGenerando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generar = async () => {
    setGenerando(true);
    setError(null);
    try {
      const inv = await api.crearInvitacion(equipoId);
      setLink(`${window.location.origin}/invitaciones/${inv.token}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo generar.');
    } finally {
      setGenerando(false);
    }
  };

  const copiar = async () => {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  };

  return (
    <section className="glass-card rounded-[6px] p-5">
      <div className="mb-1.5 flex items-center gap-2">
        <Link2 size={15} className="text-tinta-2" />
        <h2 className="text-sm font-bold text-tinta">
          Invitar a alguien que no tiene cuenta
        </h2>
      </div>
      <p className="mb-4 max-w-lg text-[13px] leading-relaxed text-tinta-3">
        Si no aparece en el buscador es porque todavía no se registró. Mandale
        este link: se crea la cuenta y queda en el equipo.
      </p>

      {error && (
        <p className="mb-3 flex items-start gap-2 rounded-[4px] border border-vivo/30 bg-vivo/10 px-3 py-2 text-[13px] text-vivo">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {error}
        </p>
      )}

      {link ? (
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded-[4px] border border-borde bg-hundida px-3.5 py-2.5 font-mono text-[12px] text-acento-claro/90">
            {link}
          </code>
          <button
            onClick={copiar}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-[4px] border border-borde px-3 py-2.5 text-xs font-semibold text-tinta-2 transition-colors hover:border-borde-fuerte hover:text-tinta"
          >
            {copiado ? <Check size={13} className="text-tinta-2" /> : <Copy size={13} />}
            {copiado ? 'Copiado' : 'Copiar'}
          </button>
          <button
            onClick={() => setLink(null)}
            title="Descartar"
            className="shrink-0 rounded-[4px] p-2.5 text-tinta-4 transition-colors hover:text-tinta-2"
          >
            <X size={14} />
          </button>
        </div>
      ) : (
        <button
          onClick={generar}
          disabled={generando}
          className="inline-flex items-center gap-2 rounded-[4px] border border-borde bg-elevada px-4 py-2 text-sm font-semibold text-acento-claro transition-colors hover:bg-borde disabled:opacity-50"
        >
          {generando ? <Loader2 size={14} className="animate-spin" /> : <Link2 size={14} />}
          Generar link de invitación
        </button>
      )}

      {link && (
        <p className="mt-2.5 text-[11px] text-tinta-4">
          Vale 7 días y se usa una sola vez.
        </p>
      )}
    </section>
  );
}
