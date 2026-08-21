'use client';

import React, { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { escucharChat } from '@/lib/eventos';
import { Partida, Usuario } from '@/types';
import { ApiMensajePartida } from '@/lib/api-types';
import {
  X, LogIn, Loader2, CheckCircle2, AlertCircle, Trophy, AlertTriangle, Send
} from 'lucide-react';

const TOKEN_KEY = 'torneos_auth_token';

interface Props {
  partida: Partida;
  onClose: () => void;
  onUpdated: () => void;
}

export default function PartidaDetailModal({ partida, onClose, onUpdated }: Props) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [misEquipoIds, setMisEquipoIds] = useState<Set<string>>(new Set());
  const [checking, setChecking] = useState(true);

  const [marcadorPropio, setMarcadorPropio] = useState(0);
  const [marcadorRival, setMarcadorRival] = useState(0);
  const [evidenciaUrl, setEvidenciaUrl] = useState('');
  const [motivoDisputa, setMotivoDisputa] = useState('');
  const [showDisputa, setShowDisputa] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [mensajes, setMensajes] = useState<ApiMensajePartida[]>([]);
  const [nuevoMensaje, setNuevoMensaje] = useState('');
  const [enviandoMensaje, setEnviandoMensaje] = useState(false);
  // Con el polling anterior, un envío fallido se recuperaba solo en el
  // siguiente ciclo y no valía la pena avisar. Ahora no hay siguiente ciclo:
  // si falla, el mensaje se perdió y el capitán tiene que saberlo.
  const [errorChat, setErrorChat] = useState<string | null>(null);
  const mensajesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setChecking(false); return; }
    api.setToken(token);
    api.getMe()
      .then(u => {
        setUsuario(u);
        return api.getMisInscripciones();
      })
      .then(mis => setMisEquipoIds(new Set((mis || []).map(m => String(m.inscripcion.equipo.id)))))
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);

  const eqA = partida.participaciones[0];
  const eqB = partida.participaciones[1];
  const miParticipacion = [eqA, eqB].find(p => p && misEquipoIds.has(p.equipoId));
  const rivalParticipacion = [eqA, eqB].find(p => p && p !== miParticipacion);
  const soyCapitan = !!miParticipacion;
  const soyOrganizador = usuario?.rol === 'organizador';
  const puedoChatear = soyCapitan || soyOrganizador;

  // El historial se pide una sola vez al abrir; a partir de ahí los mensajes
  // nuevos llegan empujados por el stream. Antes esto era un GET cada 4
  // segundos por cada modal abierto.
  useEffect(() => {
    if (!puedoChatear) return;
    let activo = true;

    api.getMensajesPartida(partida.faseId, partida.id)
      .then(m => { if (activo) setMensajes(m); })
      .catch(() => {});

    const cortar = escucharChat(partida.id, (mensaje) => {
      if (!activo) return;
      setMensajes(previos => (
        // El que escribe ya agregó su mensaje al mandarlo, y el stream se lo
        // devuelve igual: sin este chequeo lo vería duplicado.
        previos.some(m => m.id === mensaje.id) ? previos : [...previos, mensaje]
      ));
    });

    return () => { activo = false; cortar(); };
  }, [puedoChatear, partida.faseId, partida.id]);

  useEffect(() => {
    mensajesRef.current?.scrollTo({ top: mensajesRef.current.scrollHeight });
  }, [mensajes]);

  const handleEnviarMensaje = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nuevoMensaje.trim() || !puedoChatear) return;
    setEnviandoMensaje(true);
    setErrorChat(null);
    try {
      // La respuesta ya trae el mensaje creado: se agrega con eso en vez de
      // volver a pedir la lista entera. El stream lo va a devolver también,
      // y el chequeo por id de arriba evita que se vea dos veces.
      const creado = await api.enviarMensajePartida(partida.faseId, partida.id, {
        equipo_id: miParticipacion ? Number(miParticipacion.equipoId) : undefined,
        texto: nuevoMensaje.trim(),
      });
      setNuevoMensaje('');
      setMensajes(previos => (
        previos.some(m => m.id === creado.id) ? previos : [...previos, creado]
      ));
    } catch {
      setErrorChat('No se pudo enviar el mensaje. Revisá la conexión y probá de nuevo.');
    } finally {
      setEnviandoMensaje(false);
    }
  };

  const refrescarYCerrar = (msg: string) => {
    setSuccess(msg);
    onUpdated();
    setTimeout(() => onClose(), 1200);
  };

  const handleCheckIn = async () => {
    if (!miParticipacion) return;
    setLoading(true); setError(null);
    try {
      await api.checkInPartida(partida.faseId, partida.id, miParticipacion.equipoId);
      refrescarYCerrar('Presencia confirmada.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo confirmar el check-in.');
    } finally {
      setLoading(false);
    }
  };

  const handleReportar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!miParticipacion) return;
    setLoading(true); setError(null);
    try {
      await api.reportarResultado(partida.faseId, partida.id, {
        equipo_id: Number(miParticipacion.equipoId),
        marcador_propio: marcadorPropio,
        marcador_rival: marcadorRival,
        evidencia_url: evidenciaUrl.trim() || undefined,
      });
      refrescarYCerrar('Resultado reportado — esperando confirmación del rival.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo reportar el resultado.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmar = async () => {
    if (!miParticipacion) return;
    setLoading(true); setError(null);
    try {
      await api.confirmarResultadoAdmin(partida.faseId, partida.id, miParticipacion.equipoId);
      refrescarYCerrar('Resultado confirmado.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo confirmar el resultado.');
    } finally {
      setLoading(false);
    }
  };

  const handleImpugnar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!miParticipacion || !motivoDisputa.trim()) return;
    setLoading(true); setError(null);
    try {
      await api.impugnarResultado(partida.faseId, partida.id, {
        equipo_id: Number(miParticipacion.equipoId), motivo: motivoDisputa.trim(),
      });
      refrescarYCerrar('Disputa abierta — el organizador la va a revisar.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo abrir la disputa.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md" onClick={onClose}>
      <div className="w-full max-w-md bg-[#11111f] border border-slate-700 rounded-2xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="px-5 py-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <h3 className="font-extrabold text-sm text-white">Partida #{partida.id}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-2">
          {partida.participaciones.map((p) => (
            <div key={p.id} className={`flex items-center justify-between p-3 rounded-xl border text-sm ${p.esGanador ? 'bg-emerald-950/30 border-emerald-500/40' : 'bg-slate-950 border-slate-800'}`}>
              <span className={p.esGanador ? 'text-white font-bold' : 'text-slate-300'}>{p.equipo?.nombre || 'Por definir'}</span>
              <span className="font-mono font-black text-white">{p.mapasGanados ?? '—'}</span>
            </div>
          ))}
        </div>

        <div className="px-5 pb-5 space-y-3">
          {success && (
            <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 size={14} /> {success}
            </div>
          )}
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          {checking ? (
            <div className="flex items-center gap-2 text-white/40 text-xs py-2"><Loader2 size={14} className="animate-spin" /> Verificando sesión...</div>
          ) : !usuario ? (
            <div className="p-3 rounded-xl bg-violet-950/30 border border-violet-500/30 text-xs text-violet-200 flex items-center gap-2">
              <LogIn size={14} className="shrink-0" /> Iniciá sesión como capitán para reportar resultados o hacer check-in de esta partida.
            </div>
          ) : !soyCapitan ? (
            <p className="text-xs text-slate-400">Solo los capitanes de estos dos equipos pueden reportar esta partida.</p>
          ) : !success && (
            <>
              {partida.estado === 'check_in' && (
                <button
                  onClick={handleCheckIn}
                  disabled={loading}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Confirmar Presencia
                </button>
              )}

              {partida.estado === 'en_curso' && (
                <form onSubmit={handleReportar} className="space-y-2.5">
                  <p className="text-xs text-white/50">Reportá el marcador final de tu partida.</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-[11px] text-white/40 mb-1">{miParticipacion?.equipo.nombre} (vos)</label>
                      <input type="number" min={0} max={5} value={marcadorPropio} onChange={e => setMarcadorPropio(Number(e.target.value))}
                        className="w-full bg-[#0a0a14] border border-white/10 rounded-lg px-3 py-2 text-center font-mono font-bold text-white" />
                    </div>
                    <div>
                      <label className="block text-[11px] text-white/40 mb-1">{rivalParticipacion?.equipo.nombre || 'Rival'}</label>
                      <input type="number" min={0} max={5} value={marcadorRival} onChange={e => setMarcadorRival(Number(e.target.value))}
                        className="w-full bg-[#0a0a14] border border-white/10 rounded-lg px-3 py-2 text-center font-mono font-bold text-white" />
                    </div>
                  </div>
                  <input
                    type="text" value={evidenciaUrl} onChange={e => setEvidenciaUrl(e.target.value)}
                    placeholder="Link de la captura (opcional, pero recomendado)"
                    className="w-full bg-[#0a0a14] border border-white/10 rounded-lg px-3 py-2 text-xs text-white"
                  />
                  <button type="submit" disabled={loading} className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 hover:from-violet-500 text-white text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50">
                    {loading ? <Loader2 size={14} className="animate-spin" /> : <Trophy size={14} />} Reportar Resultado
                  </button>
                </form>
              )}

              {partida.estado === 'reportada' && !showDisputa && (
                <div className="space-y-2">
                  <p className="text-xs text-white/50">El rival reportó un marcador. Confirmalo si es correcto, o abrí una disputa.</p>
                  <div className="flex gap-2">
                    <button onClick={handleConfirmar} disabled={loading} className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-2 disabled:opacity-50">
                      {loading ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Confirmar
                    </button>
                    <button onClick={() => setShowDisputa(true)} className="flex-1 py-2.5 rounded-xl bg-amber-600/20 hover:bg-amber-600/40 border border-amber-500/30 text-amber-300 text-xs font-bold flex items-center justify-center gap-2">
                      <AlertTriangle size={14} /> Disputar
                    </button>
                  </div>
                </div>
              )}

              {partida.estado === 'reportada' && showDisputa && (
                <form onSubmit={handleImpugnar} className="space-y-2">
                  <textarea
                    value={motivoDisputa} onChange={e => setMotivoDisputa(e.target.value)}
                    placeholder="Explicá por qué el marcador reportado está mal..."
                    className="w-full bg-[#0a0a14] border border-amber-500/30 rounded-lg px-3 py-2 text-xs text-white h-20 resize-none"
                    required
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setShowDisputa(false)} className="flex-1 py-2 bg-white/5 hover:bg-white/10 text-white/60 text-xs rounded-xl">Cancelar</button>
                    <button type="submit" disabled={loading} className="flex-1 py-2 bg-amber-600 hover:bg-amber-500 text-black font-bold text-xs rounded-xl disabled:opacity-50">
                      {loading ? 'Enviando...' : 'Enviar Disputa'}
                    </button>
                  </div>
                </form>
              )}

              {(partida.estado === 'programada' || partida.estado === 'confirmada' || partida.estado === 'en_disputa') && (
                <p className="text-xs text-slate-400">
                  {partida.estado === 'programada' && 'El check-in todavía no se abrió para esta partida.'}
                  {partida.estado === 'confirmada' && 'Esta partida ya tiene un resultado confirmado.'}
                  {partida.estado === 'en_disputa' && 'Esta partida está en disputa — el organizador la va a resolver.'}
                </p>
              )}
            </>
          )}

          {puedoChatear && (
            <div className="pt-1 border-t border-slate-800 mt-1">
              <p className="text-[11px] font-semibold text-slate-400 pt-3 pb-1.5">
                {soyOrganizador && !soyCapitan ? 'Chat de la partida (viendo como organizador)' : 'Chat con el rival'}
              </p>
              <div ref={mensajesRef} className="h-36 overflow-y-auto space-y-1.5 bg-[#0a0a14] border border-slate-800 rounded-lg p-2.5">
                {mensajes.length === 0 ? (
                  <p className="text-[11px] text-slate-600 text-center py-4">Todavía no hay mensajes.</p>
                ) : (
                  mensajes.map(m => {
                    if (m.equipo_id === null) {
                      return (
                        <div key={m.id} className="flex justify-center">
                          <div className="max-w-[90%] rounded-lg px-2.5 py-1.5 text-xs bg-amber-500/10 border border-amber-500/20 text-amber-200">
                            <p className="text-[10px] font-semibold opacity-70 mb-0.5">{m.autor_nombre}</p>
                            <p className="break-words">{m.texto}</p>
                          </div>
                        </div>
                      );
                    }
                    const esMio = miParticipacion ? m.equipo_id === Number(miParticipacion.equipoId) : false;
                    return (
                      <div key={m.id} className={`flex ${esMio ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] rounded-lg px-2.5 py-1.5 text-xs ${esMio ? 'bg-violet-600/30 text-white' : 'bg-slate-800 text-slate-200'}`}>
                          <p className="text-[10px] font-semibold opacity-60 mb-0.5">{m.autor_nombre}</p>
                          <p className="break-words">{m.texto}</p>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
              {errorChat && (
                <p className="text-[11px] text-rose-300 pt-2 flex items-center gap-1.5">
                  <AlertCircle size={12} className="shrink-0" /> {errorChat}
                </p>
              )}
              <form onSubmit={handleEnviarMensaje} className="flex gap-2 pt-2">
                <input
                  type="text" value={nuevoMensaje} onChange={e => setNuevoMensaje(e.target.value)}
                  placeholder={soyOrganizador && !soyCapitan ? 'Escribir como organizador...' : 'Escribí un mensaje...'}
                  maxLength={500}
                  className="flex-1 bg-[#0a0a14] border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500"
                />
                <button
                  type="submit" disabled={enviandoMensaje || !nuevoMensaje.trim()}
                  className="px-3 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  <Send size={13} />
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
