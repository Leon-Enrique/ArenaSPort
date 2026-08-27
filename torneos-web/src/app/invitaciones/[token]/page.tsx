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
  ShieldX, Users,
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

  // `api.setToken` va fuera del try y antes del await a propósito: es
  // sincrónico y tiene que estar puesto ANTES de pedir el preview, si no
  // la invitación dirigida a esta persona se leería sin sesión y
  // respondería 404.
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

  // La llamada va dentro de una función async declarada acá adentro, y no
  // suelta en el cuerpo del efecto: así React ve que todos los setState
  // ocurren después de un await y no en el render, que es lo que dispara
  // cascadas.
  useEffect(() => {
    let vigente = true;
    (async () => {
      if (vigente) await cargar();
    })();
    return () => { vigente = false; };
  }, [cargar]);

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
            <div className="flex items-center justify-center gap-3 py-20 text-tinta-3">
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
                    className="flex w-full items-center justify-center gap-2 rounded-[6px] bg-acento px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-acento-hover"
                  >
                    <LogIn size={15} /> Crear mi cuenta y entrar
                  </button>
                  <p className="mt-3 text-center text-[11px] leading-relaxed text-tinta-4">
                    Cuando te registres volvés acá y entrás al equipo. Te toma
                    menos de un minuto.
                  </p>
                </>
              ) : (
                <>
                  {error && (
                    <p className="mb-3 flex items-start gap-2 rounded-[4px] border border-vivo/30 bg-vivo/10 px-3 py-2 text-[13px] text-vivo">
                      <AlertTriangle size={14} className="mt-0.5 shrink-0" /> {error}
                    </p>
                  )}
                  <button
                    onClick={entrar}
                    disabled={entrando}
                    className="flex w-full items-center justify-center gap-2 rounded-[6px] bg-acento px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-acento-hover disabled:opacity-50"
                  >
                    {entrando
                      ? <Loader2 size={15} className="animate-spin" />
                      : <ArrowRight size={15} />}
                    Entrar a {preview.equipo_nombre}
                  </button>

                  {!preview.ya_cargaste_tu_identidad && (
                    <div className="mt-4 flex items-start gap-2.5 rounded-[6px] border border-atencion/25 bg-atencion/10 px-4 py-3">
                      <Gamepad2 size={14} className="mt-0.5 shrink-0 text-atencion" />
                      <p className="text-[12px] leading-relaxed text-atencion">
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
    <div className="rounded-[8px] border border-borde bg-superficie p-8">
      <div className="text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-[6px] bg-elevada border border-borde">
          <Users size={20} className="text-tinta-2" />
        </div>

        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-tinta-3">
          {preview.dirigida_a_vos ? 'Te invitaron' : 'Invitación a un equipo'}
        </p>

        <h1 className="mb-2 text-[24px] font-bold tracking-[-0.025em] text-tinta">
          {preview.equipo_nombre}
        </h1>
        <p className="mb-7 text-[14px] leading-relaxed text-tinta-3">
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
    <div className="rounded-[8px] border border-borde bg-superficie estado-ok p-10 text-center">
      <CheckCircle2 size={32} className="mx-auto mb-4 text-ok" />
      <h1 className="mb-2 text-[19px] font-semibold tracking-[-0.02em] text-tinta">
        Ya estás en {equipo}
      </h1>
      <p className="text-sm text-tinta-3">Te llevamos a tu perfil…</p>
    </div>
  );
}

function InvitacionInvalida() {
  return (
    <div className="rounded-[8px] border border-borde bg-superficie p-10 text-center">
      <ShieldX size={34} className="mx-auto mb-4 text-tinta-4" />
      <h1 className="mb-2 text-lg font-bold text-tinta">
        Esta invitación no sirve
      </h1>
      <p className="mx-auto mb-6 max-w-xs text-sm leading-relaxed text-tinta-3">
        Puede que haya vencido, que ya se haya usado, o que el capitán la haya
        dado de baja. Pedile uno nuevo.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-acento-claro transition-colors hover:text-acento"
      >
        Ir al inicio <ArrowRight size={12} />
      </Link>
    </div>
  );
}
