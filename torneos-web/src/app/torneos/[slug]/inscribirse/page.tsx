'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api, ApiError, mapResumenAEdicion } from '@/lib/api';
import { ApiInscripcionCreada, ApiMiembroEquipo, ApiMiEquipo, ApiResumenEdicion } from '@/lib/api-types';
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

  // Equipos permanentes del usuario. Elegir uno hace que el torneo sume al
  // historial de ESE equipo en vez de crear uno nuevo y suelto.
  const [misEquipos, setMisEquipos] = useState<ApiMiEquipo[]>([]);
  const [equipoElegidoId, setEquipoElegidoId] = useState<number | null>(null);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    api.setToken(token);
    api.getMe().then(u => {
      setUsuario(u);
      setContactoNombre(prev => prev || u.nombre);
      return api.getMisEquipos();
    })
      .then(equipos => setMisEquipos(equipos || []))
      .catch(() => {});
  }, []);

  // El plantel permanente del equipo elegido. Es el punto de tener uno:
  // si ya está armado, inscribirse no debería pedir tipear a nadie.
  const [plantel, setPlantel] = useState<ApiMiembroEquipo[]>([]);
  const [cargandoPlantel, setCargandoPlantel] = useState(false);
  const [usarPlantel, setUsarPlantel] = useState(false);

  // Al elegir un equipo se copian su nombre y tag al formulario: son
  // editables, porque un equipo puede cambiar de nombre entre temporadas
  // sin dejar de ser el mismo.
  const elegirEquipo = async (id: number | null) => {
    setEquipoElegidoId(id);
    const equipo = misEquipos.find(e => e.id === id);
    if (equipo) {
      setNombreEquipo(equipo.nombre);
      setTag(equipo.tag || '');
    }

    if (id === null) {
      setPlantel([]);
      setUsarPlantel(false);
      return;
    }

    setCargandoPlantel(true);
    try {
      const miembros = await api.getMiembrosEquipo(id);
      setPlantel(miembros);
      // Si el equipo ya tiene gente, usar su plantel es lo que la persona
      // quiere el 99% de las veces. Tipear a mano queda como escape.
      setUsarPlantel(miembros.length > 0);
    } catch {
      setPlantel([]);
      setUsarPlantel(false);
    } finally {
      setCargandoPlantel(false);
    }
  };

  const plantelListo = plantel.filter(m => m.identidad);
  const plantelSinId = plantel.filter(m => !m.identidad);

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
      <div className="min-h-screen flex flex-col bg-fondo text-tinta">
        <Navbar />
        <main className="flex-1 flex items-center justify-center text-tinta-3 text-sm gap-2">
          <Loader2 className="animate-spin" size={18} /> Cargando torneo...
        </main>
        <Footer />
      </div>
    );
  }

  if (notFound || !edicion) {
    return (
      <div className="min-h-screen flex flex-col bg-fondo text-tinta">
        <Navbar />
        <main className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-4">
          <h1 className="text-xl font-bold text-white">Este torneo no existe</h1>
          <p className="text-sm text-tinta-3">Revisá el link o volvé al inicio.</p>
          <Link href="/" className="mt-2 px-5 py-2.5 rounded-[6px] accion-principal text-white text-xs font-bold">
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
        equipo_id: equipoElegidoId ?? undefined,
        nombre_equipo: nombreEquipo.trim(),
        tag: tag.trim() || undefined,
        contacto_nombre: contactoNombre.trim() || undefined,
        contacto_whatsapp: whatsapp.trim() || undefined,
        contacto_discord: discordTag.trim() || undefined,
        capitan_declarado: contactoNombre.trim() || undefined,
        // Sin `discord_id`: el backend vincula la cuenta de quien inscribe a
        // la fila del capitán y a ninguna otra. Antes se mandaba desde acá y
        // le pegaba TU cuenta a quien estuviera marcado capitán, fuera quien
        // fuera — vos reportabas en su nombre y él no podía hacer nada.
        // Sin `jugadores`, el backend arma el roster desde el plantel
        // permanente del equipo, con la identidad que cargó cada uno en su
        // cuenta. Es el sentido de tener un equipo permanente.
        jugadores: usarPlantel
          ? undefined
          : jugadores.map(j => ({
            identidad: j.identidad,
            es_suplente: j.esSuplente,
            es_capitan: j.esCapitan,
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
    <div className="min-h-screen flex flex-col bg-fondo text-tinta selection:bg-acento selection:text-white">
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-6">
        <Link
          href={`/torneos/${edicion.slug}`}
          className="inline-flex items-center gap-2 text-xs text-tinta-3 hover:text-white transition-colors"
        >
          <ArrowLeft size={14} /> Volver al Torneo ({edicion.nombre})
        </Link>

        <div className="bg-superficie border border-borde rounded-[8px] p-6 sm:p-8 shadow-2xl relative overflow-hidden space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase bg-elevada border border-acento text-acento-claro">
              {edicion.juego.nombre}
            </span>
            {edicion.bolsaPremios && (
              <>
                <span className="text-tinta-4">•</span>
                <span className="text-xs font-mono text-tinta-2 font-bold">{edicion.bolsaPremios} en Premios</span>
              </>
            )}
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Formulario de Inscripción Oficial
          </h1>
          <p className="text-xs sm:text-sm text-tinta-3 max-w-2xl">
            Postula a tu escuadra para <strong>{edicion.nombre}</strong>. Requiere exactamente {requeridos} titulares, hasta {maxSuplentes} suplentes.
          </p>
        </div>

        {resultado ? (
          <div className="bg-superficie border border-green-500/40 rounded-[8px] p-8 sm:p-12 text-center space-y-6 shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-green-500/20 border border-green-500/40 text-ok flex items-center justify-center mx-auto shadow-xl shadow-green-500/20">
              <CheckCircle2 className="w-9 h-9" />
            </div>
            <div className="space-y-2 max-w-md mx-auto">
              <h2 className="text-xl sm:text-2xl font-black text-white">¡Inscripción Enviada con Éxito!</h2>
              <p className="text-xs text-tinta-2 leading-relaxed">
                Tu postulación para <strong className="text-acento-claro">{resultado.inscripcion.equipo.nombre}</strong> quedó
                registrada en estado <strong>{resultado.inscripcion.estado}</strong>, pendiente de revisión del staff.
              </p>
            </div>

            {resultado.avisos.length > 0 && (
              <div className="p-4 bg-amber-950/30 border border-amber-500/30 rounded-[6px] max-w-md mx-auto text-xs text-left text-amber-200 space-y-1">
                {resultado.avisos.map((a, i) => <p key={i}>⚠️ {a}</p>)}
              </div>
            )}

            <div className="p-4 bg-fondo rounded-[6px] border border-borde-sutil max-w-md mx-auto text-xs text-left space-y-1.5">
              <div className="flex justify-between">
                <span className="text-tinta-3">Torneo:</span>
                <span className="font-bold text-white">{edicion.nombre}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-tinta-3">Jugadores registrados:</span>
                <span className="font-mono text-ok font-bold">{resultado.inscripcion.jugadores.length}</span>
              </div>
            </div>

            <Link
              href={`/torneos/${edicion.slug}`}
              className="inline-block px-6 py-3 bg-acento text-white rounded-[6px] text-xs font-bold transition-all"
            >
              Volver al Torneo
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="bg-superficie border border-borde rounded-[8px] p-6 sm:p-8 space-y-6 shadow-xl">
              {/* Team info */}
              <div className="space-y-4 border-b border-borde-sutil pb-6">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Trophy size={14} className="text-acento-claro" /> Datos del Equipo
                </h4>

                {misEquipos.length > 0 && (
                  <div className="space-y-2 p-4 rounded-[6px] bg-elevada border border-acento/25">
                    <label className="block text-xs font-semibold text-tinta-2">
                      ¿Con cuál de tus equipos te inscribís?
                    </label>
                    <p className="text-[11px] text-tinta-3 leading-relaxed">
                      Si elegís uno tuyo, este torneo se suma a su historial. Si creás
                      uno nuevo, arranca de cero.
                    </p>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {misEquipos.map(eq => (
                        <button
                          key={eq.id}
                          type="button"
                          onClick={() => elegirEquipo(eq.id)}
                          className={`px-3.5 py-2 rounded-[6px] text-xs font-bold border transition-all ${
                            equipoElegidoId === eq.id
                              ? 'bg-acento border-violet-400 text-white'
                              : 'bg-fondo border-borde text-tinta-2 hover:text-white hover:border-borde'
                          }`}
                        >
                          {eq.nombre}
                          {eq.torneos_jugados > 0 && (
                            <span className="ml-1.5 font-normal opacity-60">
                              · {eq.torneos_jugados} {eq.torneos_jugados === 1 ? 'torneo' : 'torneos'}
                            </span>
                          )}
                        </button>
                      ))}
                      <button
                        type="button"
                        onClick={() => elegirEquipo(null)}
                        className={`px-3.5 py-2 rounded-[6px] text-xs font-bold border transition-all ${
                          equipoElegidoId === null
                            ? 'bg-white/10 border-white/30 text-white'
                            : 'bg-fondo border-borde text-tinta-2 hover:text-white'
                        }`}
                      >
                        + Equipo nuevo
                      </button>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Nombre del Equipo *</label>
                    <input
                      type="text" required value={nombreEquipo} onChange={e => setNombreEquipo(e.target.value)}
                      placeholder="Ej. Alpha Esports"
                      className="w-full bg-fondo border border-borde rounded-[6px] px-4 py-2.5 text-xs text-white focus:outline-none focus:border-acento"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Tag (opcional)</label>
                    <input
                      type="text" value={tag} onChange={e => setTag(e.target.value)}
                      placeholder="Ej. ALP" maxLength={12}
                      className="w-full bg-fondo border border-borde rounded-[6px] px-4 py-2.5 text-xs text-white focus:outline-none focus:border-acento font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Roster desde el plantel permanente: el camino corto. */}
              {equipoElegidoId !== null && (cargandoPlantel || plantel.length > 0) && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                      <Users size={15} className="text-acento-claro" /> Alineación
                    </h4>
                    {plantel.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setUsarPlantel(v => !v)}
                        className="text-[11px] font-semibold text-acento-claro hover:text-tinta-2 transition-colors"
                      >
                        {usarPlantel ? 'Cargar otro roster a mano' : 'Usar el plantel de mi equipo'}
                      </button>
                    )}
                  </div>

                  {cargandoPlantel && (
                    <div className="flex items-center gap-2 p-4 rounded-[6px] bg-white/[0.02] border border-borde text-xs text-tinta-3">
                      <Loader2 size={13} className="animate-spin" /> Buscando tu plantel…
                    </div>
                  )}

                  {!cargandoPlantel && usarPlantel && (
                    <div className="rounded-[6px] border border-acento/25 bg-elevada p-4 space-y-3">
                      <p className="text-[11px] text-tinta-3 leading-relaxed">
                        Se inscribe tu plantel tal como está, con el ID de juego que
                        cargó cada uno. No hace falta que escribas nada.
                      </p>

                      <ul className="space-y-1.5">
                        {plantel.map(m => (
                          <li
                            key={m.id}
                            className={`flex items-center gap-2.5 rounded-[6px] border px-3 py-2 text-xs ${
                              m.identidad
                                ? 'border-borde bg-white/[0.02]'
                                : 'border-amber-500/30 bg-amber-500/8'
                            }`}
                          >
                            <div className={`w-6 h-6 rounded-[4px] shrink-0 flex items-center justify-center text-[10px] font-bold ${
                              m.identidad
                                ? 'bg-acento/25 text-tinta-2'
                                : 'bg-amber-500/20 text-atencion'
                            }`}>
                              {(m.identidad?.nick ?? m.usuario_nombre ?? '?').charAt(0).toUpperCase()}
                            </div>
                            <span className="font-semibold text-white truncate">
                              {m.identidad?.nick ?? m.usuario_nombre}
                            </span>
                            {m.identidad ? (
                              <span className="ml-auto font-mono text-[10px] text-tinta-4 shrink-0">
                                {m.identidad.id_juego}
                              </span>
                            ) : (
                              <span className="ml-auto text-[10px] text-atencion shrink-0">
                                sin ID cargado
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>

                      {plantelSinId.length > 0 && (
                        <div className="flex items-start gap-2 rounded-[6px] border border-amber-500/25 bg-amber-500/8 px-3 py-2.5">
                          <AlertCircle size={13} className="mt-0.5 shrink-0 text-atencion" />
                          <p className="text-[11px] leading-relaxed text-amber-200/90">
                            {plantelSinId.length === 1
                              ? 'Un jugador todavía no cargó su ID de juego'
                              : `${plantelSinId.length} jugadores todavía no cargaron su ID de juego`}
                            , así que no entran en esta inscripción. Solo ellos pueden
                            cargarlo — les va a llegar el aviso.
                          </p>
                        </div>
                      )}

                      <div className="flex items-center justify-between border-t border-borde pt-3 text-xs font-mono font-bold">
                        <span className="text-tinta-3 font-sans font-normal">
                          Entran a la inscripción
                        </span>
                        <span className={plantelListo.length >= requeridos ? 'text-ok' : 'text-atencion'}>
                          {plantelListo.length}/{requeridos}
                        </span>
                      </div>

                      {plantelListo.length < requeridos && (
                        <p className="text-[11px] text-atencion/80 leading-relaxed">
                          Faltan jugadores con ID cargado: el torneo pide {requeridos} y
                          no se puede entrar incompleto.{' '}
                          <Link
                            href={`/equipos/${equipoElegidoId}/roster`}
                            className="underline hover:text-amber-200"
                          >
                            Ir al plantel
                          </Link>
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Roster tipeado a mano: el camino de siempre.
                  Se DESMONTA, no se esconde con CSS. Ocultándolo, sus inputs
                  seguían en el DOM con `required` y el navegador bloqueaba el
                  envío del formulario sin decir nada: el botón no hacía nada
                  y no había forma de darse cuenta por qué. */}
              {!usarPlantel && (
              <div className="space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                    <Users size={15} className="text-acento-claro" /> Alineación
                  </h4>
                  <div className="text-xs font-mono font-bold">
                    <span className={titulares === requeridos ? 'text-ok' : 'text-atencion'}>
                      {titulares}/{requeridos} Titulares
                    </span>
                    <span className="text-tinta-4 mx-1.5">•</span>
                    <span className="text-tinta-2">{suplentes}/{maxSuplentes} Suplentes</span>
                  </div>
                </div>

                <div className="space-y-3">
                  {jugadores.map((jugador, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-[6px] border space-y-2.5 text-xs transition-all ${
                        filasEnConflicto.has(idx)
                          ? 'bg-rose-950/30 border-rose-500 ring-1 ring-rose-500/50'
                          : jugador.esSuplente ? 'bg-elevada/20 border-borde' : 'bg-elevada border-borde'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white flex items-center gap-1.5">
                          {jugador.esSuplente ? 'Suplente' : 'Titular'} #{idx + 1}
                          {jugador.esCapitan && (
                            <span
                              title={usuario
                                ? 'Esta fila queda asociada a tu cuenta: vas a ser vos quien reporte los resultados de este equipo.'
                                : 'Sin iniciar sesión, nadie queda habilitado para reportar resultados.'}
                              className="px-1.5 py-0.2 rounded bg-amber-400/20 text-atencion font-bold text-[9px] uppercase flex items-center gap-1"
                            >
                              <Crown size={9} /> Capitán{usuario ? ' (vos)' : ''}
                            </span>
                          )}
                        </span>
                        <div className="flex items-center gap-2">
                          {!jugador.esCapitan && (
                            <button type="button" onClick={() => setCapitan(idx)} className="text-[10px] text-tinta-3 hover:text-atencion font-semibold">
                              Marcar capitán
                            </button>
                          )}
                          {idx >= requeridos && (
                            <button type="button" onClick={() => quitarJugador(idx)} className="text-vivo hover:text-vivo">
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
                            className="bg-fondo border border-borde rounded-[4px] px-3 py-2 text-white text-xs focus:outline-none focus:border-acento"
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
                    className="w-full py-2.5 rounded-[6px] border border-dashed border-white/15 text-tinta-3 hover:text-white hover:border-borde-fuerte/50 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all"
                  >
                    <Plus size={14} /> Agregar suplente
                  </button>
                )}
              </div>
              )}

              {/* Contact */}
              <div className="pt-4 border-t border-borde-sutil space-y-4">
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                  <Phone size={14} className="text-ok" /> Datos de Contacto del Capitán
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Nombre del Capitán</label>
                    <input
                      type="text" value={contactoNombre} onChange={e => setContactoNombre(e.target.value)}
                      className="w-full bg-fondo border border-borde rounded-[6px] px-4 py-2.5 text-xs text-white focus:outline-none focus:border-acento"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-tinta-2 mb-1.5">WhatsApp</label>
                    <input
                      type="text" value={whatsapp} onChange={e => setWhatsapp(e.target.value)}
                      placeholder="+591 76543210"
                      className="w-full bg-fondo border border-borde rounded-[6px] px-4 py-2.5 text-xs text-white focus:outline-none focus:border-acento font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-tinta-2 mb-1.5">Discord</label>
                    <input
                      type="text" value={discordTag} onChange={e => setDiscordTag(e.target.value)}
                      placeholder="Capitan#1234"
                      className="w-full bg-fondo border border-borde rounded-[6px] px-4 py-2.5 text-xs text-white focus:outline-none focus:border-acento font-mono"
                    />
                  </div>
                </div>
              </div>

              {errorMsg && (
                <div ref={bannerError} className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-start gap-2">
                  <AlertCircle size={15} className="shrink-0 mt-0.5" />
                  <span>
                    {errorMsg}
                    {filasEnConflicto.size > 0 && (
                      <span className="block text-vivo/70 mt-1">
                        Marcamos en rojo {filasEnConflicto.size === 1 ? 'al jugador' : 'a los jugadores'} que hay que corregir.
                      </span>
                    )}
                  </span>
                </div>
              )}

              <div className="pt-4 border-t border-borde-sutil space-y-3">
                <label className="flex items-start gap-3 text-xs text-tinta-2 cursor-pointer">
                  <input
                    type="checkbox" checked={acceptRules} onChange={e => setAcceptRules(e.target.checked)}
                    className="mt-0.5 rounded bg-fondo border-white/20 text-violet-600 focus:ring-0"
                  />
                  <span>
                    He leído y acepto el <strong>Reglamento Oficial de {edicion.nombre}</strong>, me comprometo a respetar los horarios de sala y el código de conducta deportiva.
                  </span>
                </label>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-borde-sutil">
                <Link href={`/torneos/${edicion.slug}`} className="px-4 py-2.5 bg-white/5 hover:bg-white/10 text-tinta-2 text-xs font-semibold rounded-[6px]">
                  Cancelar
                </Link>
                <button
                  type="submit"
                  disabled={isSubmitting || !acceptRules}
                  className={`px-7 py-3 rounded-[6px] text-xs font-bold transition-all shadow-xl flex items-center gap-2 ${
                    acceptRules
                      ? 'bg-elevada text-white shadow-violet-600/30'
                      : 'bg-white/10 text-tinta-4 cursor-not-allowed'
                  }`}
                >
                  {isSubmitting ? (
                    <><Loader2 size={14} className="animate-spin" /> Enviando...</>
                  ) : (
                    <><Trophy size={14} className="text-atencion" /> Confirmar e Inscribir Squad</>
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
