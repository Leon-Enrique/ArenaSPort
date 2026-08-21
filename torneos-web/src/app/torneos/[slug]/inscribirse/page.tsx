'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api, ApiError, mapResumenAEdicion } from '@/lib/api';
import { ApiInscripcionCreada, ApiResumenEdicion } from '@/lib/api-types';
import { Edicion, Usuario } from '@/types';
import {
  Trophy, Users, CheckCircle2, ArrowLeft, Crown,
  AlertCircle, Phone, Plus, Trash2, Loader2
} from 'lucide-react';

const TOKEN_KEY = 'torneos_auth_token';

interface FilaJugador {
  identidad: Record<string, string>;
  esSuplente: boolean;
  esCapitan: boolean;
}

export default function InscribirseTorneoPage() {
  const params = useParams();
  const slug = params?.slug as string;

  const [resumen, setResumen] = useState<ApiResumenEdicion | null>(null);
  const [edicion, setEdicion] = useState<Edicion | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  useEffect(() => {
    let activo = true;
    api.getEdicionBySlug(slug)
      .then(r => {
        if (!activo) return;
        if (!r) { setNotFound(true); return; }
        setResumen(r);
        setEdicion(mapResumenAEdicion(r));
      })
      .catch(() => activo && setNotFound(true))
      .finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, [slug]);

  // Form state
  const [nombreEquipo, setNombreEquipo] = useState('');
  const [tag, setTag] = useState('');
  const [contactoNombre, setContactoNombre] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [discordTag, setDiscordTag] = useState('');
  const [jugadores, setJugadores] = useState<FilaJugador[]>([]);
  const [acceptRules, setAcceptRules] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const bannerError = useRef<HTMLDivElement>(null);
  const [resultado, setResultado] = useState<ApiInscripcionCreada | null>(null);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    api.setToken(token);
    api.getMe().then(u => {
      setUsuario(u);
      setContactoNombre(prev => prev || u.nombre);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!edicion) return;
    const requeridos = edicion.juego.titularesRequeridos || 5;
    setJugadores(
      Array.from({ length: requeridos }).map((_, i) => ({
        identidad: {},
        esSuplente: false,
        esCapitan: i === 0,
      }))
    );
  }, [edicion]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100">
        <Navbar />
        <main className="flex-1 flex items-center justify-center text-white/40 text-sm gap-2">
          <Loader2 className="animate-spin" size={18} /> Cargando torneo...
        </main>
        <Footer />
      </div>
    );
  }

  if (notFound || !edicion) {
    return (
      <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100">
        <Navbar />
        <main className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-4">
          <h1 className="text-xl font-bold text-white">Este torneo no existe</h1>
          <p className="text-sm text-white/50">Revisá el link o volvé al inicio.</p>
          <Link href="/" className="mt-2 px-5 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold">
            Volver al inicio
          </Link>
        </main>
        <Footer />
      </div>
    );
  }

  const campos = edicion.juego.camposIdentidad;
  const requeridos = edicion.juego.titularesRequeridos;
  const maxSuplentes = edicion.juego.suplentesMaximos;
  const titulares = jugadores.filter(j => !j.esSuplente).length;
  const suplentes = jugadores.filter(j => j.esSuplente).length;

  const setCampo = (idx: number, key: string, value: string) => {
    setJugadores(prev => prev.map((j, i) => i === idx ? { ...j, identidad: { ...j.identidad, [key]: value } } : j));
  };

  const toggleSuplente = (idx: number) => {
    setJugadores(prev => prev.map((j, i) => i === idx ? { ...j, esSuplente: !j.esSuplente } : j));
  };

  const setCapitan = (idx: number) => {
    setJugadores(prev => prev.map((j, i) => ({ ...j, esCapitan: i === idx })));
  };

  const agregarSuplente = () => {
    if (suplentes >= maxSuplentes) return;
    setJugadores(prev => [...prev, { identidad: {}, esSuplente: true, esCapitan: false }]);
  };

  const quitarJugador = (idx: number) => {
    setJugadores(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!nombreEquipo.trim()) {
      setErrorMsg('Ingresá el nombre de tu equipo.');
      return;
    }
    if (!acceptRules) {
      setErrorMsg('Debes aceptar el reglamento oficial del torneo.');
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await api.createInscripcion(edicion.id, {
        nombre_equipo: nombreEquipo.trim(),
        tag: tag.trim() || undefined,
        contacto_nombre: contactoNombre.trim() || undefined,
        contacto_whatsapp: whatsapp.trim() || undefined,
        contacto_discord: discordTag.trim() || undefined,
        capitan_declarado: contactoNombre.trim() || undefined,
        jugadores: jugadores.map(j => ({
          identidad: j.identidad,
          es_suplente: j.esSuplente,
          es_capitan: j.esCapitan,
          discord_id: (j.esCapitan && usuario) ? usuario.discordId : undefined,
        })),
      });
      setResultado(data);
    } catch (err) {
      const mensaje = err instanceof ApiError ? err.message : 'No se pudo enviar la inscripción. Intentá de nuevo.';
      setErrorMsg(mensaje);
      // El formulario es largo: sin esto el usuario aprieta "Enviar", el
      // banner aparece arriba fuera de pantalla y parece que no pasó nada.
      requestAnimationFrame(() => {
        bannerError.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  /** Filas cuyo jugador el backend nombró en el error (ej. "Lyon ya está
   *  inscrito en el equipo 'Dragons'"). Marcarlas evita que el capitán tenga
   *  que cruzar el texto del mensaje contra el roster a ojo. */
  const filasEnConflicto = new Set<number>();
  if (errorMsg) {
    jugadores.forEach((j, idx) => {
      const valores = Object.values(j.identidad).map(v => v.trim()).filter(v => v.length >= 2);
      if (valores.some(v => errorMsg.includes(v))) filasEnConflicto.add(idx);
    });
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#070710] text-slate-100 selection:bg-violet-600 selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-6">
        <Link
          href={`/torneos/${edicion.slug}`}
          className="inline-flex items-center gap-2 text-xs text-white/40 hover:text-white transition-colors"
        >
          <ArrowLeft size={14} /> Volver al Torneo ({edicion.nombre})
        </Link>

        <div className="bg-[#11111f] border border-white/10 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase bg-violet-950 border border-violet-500 text-violet-300">
              {edicion.juego.nombre}
            </span>
            {edicion.bolsaPremios && (
              <>
                <span className="text-white/30">•</span>
                <span className="text-xs font-mono text-cyan-400 font-bold">{edicion.bolsaPremios} en Premios</span>
              </>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Formulario de Inscripción Oficial
          </h1>
          <p className="text-xs sm:text-sm text-white/50 max-w-2xl">
            Postula a tu escuadra para <strong>{edicion.nombre}</strong>. Requiere exactamente {requeridos} titulares, hasta {maxSuplentes} suplentes.
          </p>
        </div>

        {resultado ? (
          <div className="bg-[#11111f] border border-green-500/40 rounded-3xl p-8 sm:p-12 text-center space-y-6 shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-green-500/20 border border-green-500/40 text-green-400 flex items-center justify-center mx-auto shadow-xl shadow-green-500/20">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <div className="space-y-2 max-w-md mx-auto">
              <h2 className="text-xl sm:text-2xl font-black text-white">¡Inscripción Enviada con Éxito!</h2>
              <p className="text-xs text-white/60 leading-relaxed">
                Tu postulación para <strong className="text-violet-300">{resultado.inscripcion.equipo.nombre}</strong> quedó
                registrada en estado <strong>{resultado.inscripcion.estado}</strong>, pendiente de revisión del staff.
              </p>
            </div>

            {resultado.avisos.length > 0 && (
              <div className="p-4 bg-amber-950/30 border border-amber-500/30 rounded-2xl max-w-md mx-auto text-xs text-left text-amber-200 space-y-1">
                {resultado.avisos.map((a, i) => <p key={i}>⚠️ {a}</p>)}
              </div>
            )}

            <div className="p-4 bg-[#0a0a14] rounded-2xl border border-white/5 max-w-md mx-auto text-xs text-left space-y-1.5">
              <div className="flex justify-between">
                <span className="text-white/40">Torneo:</span>
                <span className="font-bold text-white">{edicion.nombre}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/40">Jugadores registrados:</span>
                <span className="font-mono text-green-400 font-bold">{resultado.inscripcion.jugadores.length}</span>
              </div>
            </div>

            <Link
              href={`/torneos/${edicion.slug}`}
              className="inline-block px-6 py-3 bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-violet-600/25 transition-all"
            >
              Volver al Torneo
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="bg-[#11111f] border border-white/8 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xl">
              {/* Team info */}
              <div className="space-y-4 border-b border-white/5 pb-6">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Trophy size={14} className="text-violet-400" /> Datos del Equipo
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-white/60 mb-1.5">Nombre del Equipo *</label>
                    <input
                      type="text" required value={nombreEquipo} onChange={e => setNombreEquipo(e.target.value)}
                      placeholder="Ej. Alpha Esports"
                      className="w-full bg-[#0a0a14] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-white/60 mb-1.5">Tag (opcional)</label>
                    <input
                      type="text" value={tag} onChange={e => setTag(e.target.value)}
                      placeholder="Ej. ALP" maxLength={12}
                      className="w-full bg-[#0a0a14] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Roster */}
              <div className="space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                    <Users size={15} className="text-violet-400" /> Alineación
                  </h4>
                  <div className="text-xs font-mono font-bold">
                    <span className={titulares === requeridos ? 'text-green-400' : 'text-amber-400'}>
                      {titulares}/{requeridos} Titulares
                    </span>
                    <span className="text-white/30 mx-1.5">•</span>
                    <span className="text-white/60">{suplentes}/{maxSuplentes} Suplentes</span>
                  </div>
                </div>

                <div className="space-y-3">
                  {jugadores.map((jugador, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-2xl border space-y-2.5 text-xs transition-all ${
                        filasEnConflicto.has(idx)
                          ? 'bg-rose-950/30 border-rose-500 ring-1 ring-rose-500/50'
                          : jugador.esSuplente ? 'bg-cyan-950/20 border-cyan-500/40' : 'bg-violet-950/20 border-violet-500/40'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white flex items-center gap-1.5">
                          {jugador.esSuplente ? 'Suplente' : 'Titular'} #{idx + 1}
                          {jugador.esCapitan && (
                            <span className="px-1.5 py-0.2 rounded bg-amber-400/20 text-amber-300 font-bold text-[9px] uppercase flex items-center gap-1">
                              <Crown size={9} /> Capitán
                            </span>
                          )}
                        </span>
                        <div className="flex items-center gap-2">
                          {!jugador.esCapitan && (
                            <button type="button" onClick={() => setCapitan(idx)} className="text-[10px] text-white/40 hover:text-amber-300 font-semibold">
                              Marcar capitán
                            </button>
                          )}
                          {idx >= requeridos && (
                            <button type="button" onClick={() => quitarJugador(idx)} className="text-rose-400 hover:text-rose-300">
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        {campos.map(campo => (
                          <input
                            key={campo.key}
                            type="text"
                            required={campo.required}
                            value={jugador.identidad[campo.key] || ''}
                            onChange={e => setCampo(idx, campo.key, e.target.value)}
                            placeholder={campo.label}
                            className="bg-[#0a0a14] border border-white/10 rounded-lg px-3 py-2 text-white text-xs focus:outline-none focus:border-violet-500"
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {suplentes < maxSuplentes && (
                  <button
                    type="button"
                    onClick={agregarSuplente}
                    className="w-full py-2.5 rounded-xl border border-dashed border-white/15 text-white/50 hover:text-white hover:border-cyan-500/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                  >
                    <Plus size={14} /> Agregar suplente
                  </button>
                )}
              </div>

              {/* Contact */}
              <div className="pt-4 border-t border-white/5 space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Phone size={14} className="text-green-400" /> Datos de Contacto del Capitán
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-white/60 mb-1.5">Nombre del Capitán</label>
                    <input
                      type="text" value={contactoNombre} onChange={e => setContactoNombre(e.target.value)}
                      className="w-full bg-[#0a0a14] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-white/60 mb-1.5">WhatsApp</label>
                    <input
                      type="text" value={whatsapp} onChange={e => setWhatsapp(e.target.value)}
                      placeholder="+591 76543210"
                      className="w-full bg-[#0a0a14] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-white/60 mb-1.5">Discord</label>
                    <input
                      type="text" value={discordTag} onChange={e => setDiscordTag(e.target.value)}
                      placeholder="Capitan#1234"
                      className="w-full bg-[#0a0a14] border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-violet-500 font-mono"
                    />
                  </div>
                </div>
              </div>

              {errorMsg && (
                <div ref={bannerError} className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-start gap-2">
                  <AlertCircle size={15} className="shrink-0 mt-0.5" />
                  <span>
                    {errorMsg}
                    {filasEnConflicto.size > 0 && (
                      <span className="block text-rose-400/70 mt-1">
                        Marcamos en rojo {filasEnConflicto.size === 1 ? 'al jugador' : 'a los jugadores'} que hay que corregir.
                      </span>
                    )}
                  </span>
                </div>
              )}

              <div className="pt-4 border-t border-white/5 space-y-3">
                <label className="flex items-start gap-3 text-xs text-white/70 cursor-pointer">
                  <input
                    type="checkbox" checked={acceptRules} onChange={e => setAcceptRules(e.target.checked)}
                    className="mt-0.5 rounded bg-[#0a0a14] border-white/20 text-violet-600 focus:ring-0"
                  />
                  <span>
                    He leído y acepto el <strong>Reglamento Oficial de {edicion.nombre}</strong>, me comprometo a respetar los horarios de sala y el código de conducta deportiva.
                  </span>
                </label>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-white/5">
                <Link href={`/torneos/${edicion.slug}`} className="px-4 py-2.5 bg-white/5 hover:bg-white/10 text-white/60 text-xs font-semibold rounded-xl">
                  Cancelar
                </Link>
                <button
                  type="submit"
                  disabled={isSubmitting || !acceptRules}
                  className={`px-7 py-3 rounded-2xl text-xs font-bold transition-all shadow-xl flex items-center gap-2 ${
                    acceptRules
                      ? 'bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-500 hover:from-violet-500 text-white shadow-violet-600/30'
                      : 'bg-white/10 text-white/30 cursor-not-allowed'
                  }`}
                >
                  {isSubmitting ? (
                    <><Loader2 size={14} className="animate-spin" /> Enviando...</>
                  ) : (
                    <><Trophy size={14} className="text-amber-300" /> Confirmar e Inscribir Squad</>
                  )}
                </button>
              </div>
            </div>
          </form>
        )}
      </main>

      <Footer />
    </div>
  );
}
