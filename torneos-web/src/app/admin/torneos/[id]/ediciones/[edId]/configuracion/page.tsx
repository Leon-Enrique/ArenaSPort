'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft, Bell, CheckCircle2, DoorOpen, Loader2, Save, Send, AlertTriangle,
} from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { ApiEdicion } from '@/lib/api-types';

export default function ConfiguracionEdicionPage() {
  const params = useParams();
  const torneoId = String(params.id);
  const edicionId = String(params.edId);

  const [edicion, setEdicion] = useState<ApiEdicion | null>(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);
  const [probando, setProbando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<string | null>(null);

  const [webhook, setWebhook] = useState('');
  const [requiereAprobacion, setRequiereAprobacion] = useState(true);
  const [requiereEquipoPermanente, setRequiereEquipoPermanente] = useState(false);
  const [bolsaPremios, setBolsaPremios] = useState('');
  const [reglamentoUrl, setReglamentoUrl] = useState('');
  const [maxEquipos, setMaxEquipos] = useState('');

  useEffect(() => {
    api.getEdicionById(edicionId)
      .then(ed => {
        setEdicion(ed);
        setWebhook(ed.discord_webhook_url ?? '');
        setRequiereAprobacion(ed.requiere_aprobacion);
        setRequiereEquipoPermanente(ed.requiere_equipo_permanente);
        setBolsaPremios(ed.bolsa_premios ?? '');
        setReglamentoUrl(ed.reglamento_url ?? '');
        setMaxEquipos(ed.max_equipos ? String(ed.max_equipos) : '');
      })
      .catch(e => setError(e instanceof ApiError ? e.message : 'No se pudo cargar la edición.'))
      .finally(() => setCargando(false));
  }, [edicionId]);

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    setExito(null);
    try {
      const actualizada = await api.updateEdicion(edicionId, {
        discord_webhook_url: webhook.trim() || null,
        requiere_aprobacion: requiereAprobacion,
        requiere_equipo_permanente: requiereEquipoPermanente,
        bolsa_premios: bolsaPremios.trim() || null,
        reglamento_url: reglamentoUrl.trim() || null,
        max_equipos: maxEquipos ? Number(maxEquipos) : null,
      });
      setEdicion(actualizada);
      setExito('Cambios guardados.');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudieron guardar los cambios.');
    } finally {
      setGuardando(false);
    }
  };

  const probar = async () => {
    setProbando(true);
    setError(null);
    setExito(null);
    try {
      const r = await api.probarWebhook(edicionId);
      setExito(r.mensaje);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo enviar el mensaje de prueba.');
    } finally {
      setProbando(false);
    }
  };

  if (cargando) {
    return (
      <div className="flex items-center justify-center gap-2 text-tinta-3 text-sm py-24">
        <Loader2 className="animate-spin" size={16} /> Cargando configuración...
      </div>
    );
  }

  if (!edicion) {
    return (
      <div className="p-6 text-sm text-vivo">
        {error ?? 'La edición no existe.'}
      </div>
    );
  }

  // El webhook guardado es el que usa el backend para enviar; si el campo tiene
  // cambios sin guardar, probar mediría el valor viejo y confundiría.
  const hayCambiosSinGuardarEnWebhook = webhook.trim() !== (edicion.discord_webhook_url ?? '');

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link href={`/admin/torneos/${torneoId}`} className="text-tinta-3 hover:text-white transition-colors">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-white">Configuración</h1>
          <p className="text-xs text-tinta-3">{edicion.nombre}</p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-start gap-2">
          <AlertTriangle size={15} className="shrink-0 mt-0.5" /> <span>{error}</span>
        </div>
      )}
      {exito && (
        <div className="p-3 rounded-[6px] bg-ok/15 border border-ok/40 text-ok text-xs flex items-center gap-2">
          <CheckCircle2 size={15} /> <span>{exito}</span>
        </div>
      )}

      {/* NOTIFICACIONES */}
      <section className="glass-card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Bell size={16} className="text-acento-claro" />
          <h2 className="text-base font-bold text-white">Avisos por Discord</h2>
        </div>
        <p className="text-xs text-tinta-3 leading-relaxed">
          Los avisos de este torneo (inscripción aprobada o rechazada, horario de partida
          confirmado, check-in abierto) se publican en el canal de Discord que elijas, mencionando
          a los jugadores involucrados. Dejalo vacío para no publicar en Discord: las
          notificaciones dentro de la plataforma funcionan igual.
        </p>

        <div>
          <label className="block text-xs font-semibold text-tinta-3 uppercase tracking-wider mb-2">
            URL del webhook
          </label>
          <input
            type="url"
            value={webhook}
            onChange={e => setWebhook(e.target.value)}
            placeholder="https://discord.com/api/webhooks/..."
            className="w-full bg-white/5 border border-borde text-white rounded-[6px] px-4 py-3 text-sm focus:outline-none focus:border-acento placeholder:text-tinta-4"
          />
          <p className="text-[11px] text-tinta-4 mt-2">
            En Discord: Configuración del canal → Integraciones → Webhooks → Copiar URL.
          </p>
        </div>

        <button
          onClick={probar}
          disabled={probando || !edicion.discord_webhook_url || hayCambiosSinGuardarEnWebhook}
          title={
            hayCambiosSinGuardarEnWebhook
              ? 'Guardá los cambios antes de probar'
              : !edicion.discord_webhook_url
                ? 'Configurá un webhook primero'
                : undefined
          }
          className="flex items-center gap-2 px-4 py-2 rounded-[6px] bg-white/5 hover:bg-white/10 border border-borde hover:border-white/25 text-tinta-2 hover:text-white text-xs font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {probando ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          Enviar mensaje de prueba
        </button>
      </section>

      {/* INSCRIPCIONES */}
      <section className="glass-card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <DoorOpen size={16} className="text-tinta-2" />
          <h2 className="text-base font-bold text-white">Inscripciones</h2>
        </div>

        <label className="flex items-start gap-3 p-4 rounded-[6px] bg-white/5 border border-borde cursor-pointer hover:border-borde transition-all">
          <input
            type="checkbox"
            checked={!requiereAprobacion}
            onChange={e => setRequiereAprobacion(!e.target.checked)}
            className="mt-0.5 w-4 h-4 accent-acento"
          />
          <span>
            <span className="block text-sm font-semibold text-white">Torneo abierto</span>
            <span className="block text-xs text-tinta-3 mt-1 leading-relaxed">
              Cualquier equipo que se inscriba queda aprobado al instante, sin que tengas que
              revisar uno por uno. Se siguen validando el cupo máximo, el plazo de inscripción, el
              roster completo y que ningún jugador esté ya en otro equipo — &quot;abierto&quot; es
              sin revisión, no sin reglas.
            </span>
          </span>
        </label>

        <label className="flex items-start gap-3 p-4 rounded-[6px] bg-white/5 border border-borde cursor-pointer hover:border-borde transition-all">
          <input
            type="checkbox"
            checked={requiereEquipoPermanente}
            onChange={e => setRequiereEquipoPermanente(e.target.checked)}
            className="mt-0.5 w-4 h-4 accent-acento"
          />
          <span>
            <span className="block text-sm font-semibold text-white">Exigir equipo permanente</span>
            <span className="block text-xs text-tinta-3 mt-1 leading-relaxed">
              Para anotarse hay que iniciar sesión y elegir un equipo ya creado, así este torneo
              suma al historial de ese equipo. Prendelo si querés que los perfiles acumulen
              récord entre temporadas. Apagado —el default— cualquiera se inscribe sin cuenta,
              que es lo más cómodo para un torneo de base.
            </span>
          </span>
        </label>

        <div>
          <label className="block text-xs font-semibold text-tinta-3 uppercase tracking-wider mb-2">
            Cupo máximo de equipos
          </label>
          <input
            type="number"
            min={2}
            value={maxEquipos}
            onChange={e => setMaxEquipos(e.target.value)}
            placeholder="Sin límite"
            className="w-full bg-white/5 border border-borde text-white rounded-[6px] px-4 py-3 text-sm focus:outline-none focus:border-acento placeholder:text-tinta-4"
          />
        </div>
      </section>

      {/* DATOS DEL TORNEO */}
      <section className="glass-card p-6 space-y-4">
        <h2 className="text-base font-bold text-white">Datos públicos</h2>

        <div>
          <label className="block text-xs font-semibold text-tinta-3 uppercase tracking-wider mb-2">
            Bolsa de premios
          </label>
          <input
            type="text"
            value={bolsaPremios}
            onChange={e => setBolsaPremios(e.target.value)}
            placeholder="Bs 5.000"
            className="w-full bg-white/5 border border-borde text-white rounded-[6px] px-4 py-3 text-sm focus:outline-none focus:border-acento placeholder:text-tinta-4"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-tinta-3 uppercase tracking-wider mb-2">
            Link del reglamento
          </label>
          <input
            type="url"
            value={reglamentoUrl}
            onChange={e => setReglamentoUrl(e.target.value)}
            placeholder="https://..."
            className="w-full bg-white/5 border border-borde text-white rounded-[6px] px-4 py-3 text-sm focus:outline-none focus:border-acento placeholder:text-tinta-4"
          />
        </div>
      </section>

      <button
        onClick={guardar}
        disabled={guardando}
        className="flex items-center gap-2 px-5 py-3 rounded-[6px] bg-acento text-white font-bold text-xs transition-all disabled:opacity-50"
      >
        {guardando ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
        Guardar cambios
      </button>
    </div>
  );
}
