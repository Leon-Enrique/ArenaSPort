'use client';

/**
 * La página del link de invitación.
 *
 * Es la única pantalla de la app que puede ver alguien que no tiene cuenta
 * —para eso existe el link— así que asume cero contexto: dice qué equipo lo
 * invita antes de pedirle nada. Devolverle un login pelado sería mandarlo a
 * registrarse sin decirle para qué.
 *
 * El token viaja en la URL, así que sobrevive al registro: se crea la
 * cuenta y se vuelve acá mismo con el link intacto.
 */

import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  AlertTriangle, ArrowRight, CheckCircle2, Gamepad2, Loader2, LogIn,
  ShieldX, Sparkles, Users,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import AuthModal from '@/components/AuthModal';
import { api, ApiError } from '@/lib/api';
import { ApiInvitacionPreview } from '@/lib/api-types';

const TOKEN_KEY = 'torneos_auth_token';

export default function InvitacionPage() {
  const params = useParams();
  const router = useRouter();
  const token = String(params.token);

  const [preview, setPreview] = useState<ApiInvitacionPreview | null>(null);
  const [cargando, setCargando] = useState(true);
  const [invalida, setInvalida] = useState(false);
  const [authAbierto, setAuthAbierto] = useState(false);
  const [entrando, setEntrando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listo, setListo] = useState(false);

  const cargar = useCallback(async () => {
    const sesion = localStorage.getItem(TOKEN_KEY);
    if (sesion) api.setToken(sesion);
    try {
      setPreview(await api.verInvitacion(token));
    } catch {
      setInvalida(true);
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => { cargar(); }, [cargar]);

  const entrar = async () => {
    setEntrando(true);
    setError(null);
    try {
      await api.aceptarInvitacion(token);
      setListo(true);
      setTimeout(() => router.push('/perfil'), 1800);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo entrar al equipo.');
      setEntrando(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex flex-1 items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          {cargando && (
            <div className="flex items-center justify-center gap-3 py-20 text-white/40">
              <Loader2 size={18} className="animate-spin" />
              <span className="text-sm">Abriendo la invitación…</span>
            </div>
          )}

          {!cargando && invalida && <InvitacionInvalida />}

          {!cargando && preview && !listo && (
            <Tarjeta preview={preview}>
              {preview.necesitas_cuenta ? (
                <>
                  <button
                    onClick={() => setAuthAbierto(true)}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-purple-900/40 transition-opacity hover:opacity-90"
                  >
                    <LogIn size={15} /> Crear mi cuenta y entrar
                  </button>
                  <p className="mt-3 text-center text-[11px] leading-relaxed text-white/30">
                    Cuando te registres volvés acá y entrás al equipo. Te toma
                    menos de un minuto.
                  </p>
                </>
              ) : (
                <>
                  {error && (
                    <p className="mb-3 flex items-start gap-2 rounded-lg border border-red-500/25 bg-red-500/8 px-3 py-2 text-[13px] text-red-300">
                      <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {error}
                    </p>
                  )}
                  <button
                    onClick={entrar}
                    disabled={entrando}
                    className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-purple-900/40 transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    {entrando
                      ? <Loader2 size={15} className="animate-spin" />
                      : <ArrowRight size={15} />}
                    Entrar a {preview.equipo_nombre}
                  </button>

                  {!preview.ya_cargaste_tu_identidad && (
                    <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/8 px-4 py-3">
                      <Gamepad2 size={14} className="mt-0.5 shrink-0 text-amber-400" />
                      <p className="text-[12px] leading-relaxed text-amber-200/85">
                        Después vas a tener que cargar tu ID de{' '}
                        {preview.juego_nombre} en tu perfil. Sin eso no te
                        pueden inscribir en los torneos.
                      </p>
                    </div>
                  )}
                </>
              )}
            </Tarjeta>
          )}

          {listo && preview && <YaEstas equipo={preview.equipo_nombre} />}
        </div>
      </main>
      <Footer />

      {/* Al volver del registro se recarga el preview con la sesión nueva:
          el token sigue en la URL, así que no se pierde la invitación. */}
      <AuthModal
        isOpen={authAbierto}
        onClose={() => setAuthAbierto(false)}
        onLoggedIn={() => {
          setAuthAbierto(false);
          setCargando(true);
          cargar();
        }}
      />
    </div>
  );
}

function Tarjeta({
  preview, children,
}: {
  preview: ApiInvitacionPreview;
  children: React.ReactNode;
}) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-slate-900/90 to-slate-950/95 p-8 shadow-2xl shadow-black/40">
      <div className="pointer-events-none absolute -top-28 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full bg-purple-600/20 blur-3xl" />

      <div className="relative text-center">
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-purple-900/40">
          <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-slate-950">
            <Users size={24} className="text-purple-300" />
          </div>
        </div>

        <p className="mb-1.5 flex items-center justify-center gap-1.5 text-[11px] font-semibold uppercase tracking-widest text-cyan-400">
          <Sparkles size={10} />
          {preview.dirigida_a_vos ? 'Te invitaron' : 'Invitación a un equipo'}
        </p>

        <h1 className="mb-2 text-2xl font-extrabold tracking-tight text-white">
          {preview.equipo_nombre}
        </h1>
        <p className="mb-7 text-sm leading-relaxed text-white/45">
          Te suman al plantel de {preview.juego_nombre}. Vas a poder salirte
          solo cuando quieras.
        </p>

        {children}
      </div>
    </div>
  );
}

function YaEstas({ equipo }: { equipo: string }) {
  return (
    <div className="rounded-3xl border border-cyan-500/25 bg-gradient-to-b from-cyan-500/10 to-slate-950/95 p-10 text-center shadow-2xl shadow-black/40">
      <CheckCircle2 size={40} className="mx-auto mb-4 text-cyan-400" />
      <h1 className="mb-2 text-xl font-extrabold text-white">
        Ya estás en {equipo}
      </h1>
      <p className="text-sm text-white/45">Te llevamos a tu perfil…</p>
    </div>
  );
}

function InvitacionInvalida() {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-10 text-center">
      <ShieldX size={34} className="mx-auto mb-4 text-white/25" />
      <h1 className="mb-2 text-lg font-bold text-white">
        Esta invitación no sirve
      </h1>
      <p className="mx-auto mb-6 max-w-xs text-sm leading-relaxed text-white/40">
        Puede que haya vencido, que ya se haya usado, o que el capitán la haya
        dado de baja. Pedile uno nuevo.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-400 transition-colors hover:text-purple-300"
      >
        Ir al inicio <ArrowRight size={12} />
      </Link>
    </div>
  );
}
