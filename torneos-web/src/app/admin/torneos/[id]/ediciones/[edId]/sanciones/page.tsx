'use client';

/**
 * PROTOTIPO DE INTERFAZ — no funciona.
 *
 * Se conserva a propósito como referencia de diseño para cuando se
 * implementen las sanciones de verdad. Hoy:
 *
 *   - Los datos son de `mock-data`, no de la base. Nada de lo que se ve acá
 *     existe.
 *   - Lo que se cargue vive en el estado de React y desaparece al recargar.
 *   - No hay modelo `Sancion` ni endpoints en el backend: no hay nada
 *     detrás de esta pantalla.
 *   - La ruta no está enlazada desde ningún menú; se llega solo escribiendo
 *     la URL.
 *
 * Si alguien la enlaza sin implementar el backend, un organizador va a creer
 * que sancionó a un equipo y no va a haber pasado nada.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Flag, AlertTriangle, ShieldX, Ban, UserX, Plus,
  CheckCircle2, Clock, Trash2, Calendar, FileText, ChevronRight
} from 'lucide-react';
import {
  MOCK_TORNEOS, MOCK_EDICIONES, MOCK_EQUIPOS, MOCK_ROSTERS
} from '@/lib/mock-data';

interface Sancion {
  id: string;
  tipo: 'advertencia' | 'deduccion_puntos' | 'default_loss' | 'descalificacion' | 'ban_jugador';
  equipoId: string;
  equipoNombre: string;
  jugadorNick?: string;
  motivo: string;
  articuloReglamento: string;
  gravedad: 'leve' | 'moderada' | 'grave';
  fecha: string;
  aplicadoPor: string;
}

const TIPO_BADGE = {
  advertencia: { label: 'Advertencia Oficial', color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30', icon: <AlertTriangle size={13} /> },
  deduccion_puntos: { label: 'Deducción de Puntos', color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: <Flag size={13} /> },
  default_loss: { label: 'Derrota por W.O.', color: 'bg-orange-500/15 text-orange-400 border-orange-500/30', icon: <ShieldX size={13} /> },
  descalificacion: { label: 'Descalificación del Torneo', color: 'bg-red-500/15 text-red-400 border-red-500/30', icon: <Ban size={13} /> },
  ban_jugador: { label: 'Suspensión de Jugador', color: 'bg-rose-500/15 text-rose-400 border-rose-500/30', icon: <UserX size={13} /> },
};

export default function EdicionSancionesAdminPage() {
  const params = useParams();
  const torneoId = params.id as string;
  const edId = params.edId as string;

  const torneo = MOCK_TORNEOS.find(t => t.id === torneoId) ?? MOCK_TORNEOS[0];
  const edicion = MOCK_EDICIONES.find(e => e.id === edId) ?? MOCK_EDICIONES[0];

  const [sancionesList, setSancionesList] = useState<Sancion[]>([
    {
      id: 'sanc-1',
      tipo: 'advertencia',
      equipoId: 'eq-2',
      equipoNombre: 'Cyber Titans',
      motivo: 'Falta de respeto en chat general del lobby hacia el equipo rival',
      articuloReglamento: 'Art. 7.1 - Código de Conducta y Fair Play',
      gravedad: 'leve',
      fecha: '2026-08-16 14:30',
      aplicadoPor: 'Admin Principal'
    },
    {
      id: 'sanc-2',
      tipo: 'deduccion_puntos',
      equipoId: 'eq-4',
      equipoNombre: 'Nova Squad',
      motivo: 'Demora injustificada superior a 20 minutos en presentarse al match',
      articuloReglamento: 'Art. 4.3 - Puntualidad y Check-in',
      gravedad: 'moderada',
      fecha: '2026-08-15 19:45',
      aplicadoPor: 'Admin Principal'
    }
  ]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedEquipoId, setSelectedEquipoId] = useState(MOCK_EQUIPOS[0].id);
  const [tipo, setTipo] = useState<Sancion['tipo']>('advertencia');
  const [gravedad, setGravedad] = useState<Sancion['gravedad']>('leve');
  const [articulo, setArticulo] = useState('Art. 7.1 - Código de Conducta');
  const [motivo, setMotivo] = useState('');
  const [jugadorNick, setJugadorNick] = useState('');
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const handleCreateSanction = (e: React.FormEvent) => {
    e.preventDefault();
    const equipo = MOCK_EQUIPOS.find(eq => eq.id === selectedEquipoId);
    if (!equipo || !motivo) return;

    const newSancion: Sancion = {
      id: `sanc-${Date.now()}`,
      tipo,
      equipoId: equipo.id,
      equipoNombre: equipo.nombre,
      jugadorNick: jugadorNick || undefined,
      motivo,
      articuloReglamento: articulo,
      gravedad,
      fecha: new Date().toISOString().slice(0, 16).replace('T', ' '),
      aplicadoPor: 'Administrador'
    };

    setSancionesList(prev => [newSancion, ...prev]);
    setIsModalOpen(false);
    setMotivo('');
    setJugadorNick('');
    showToast(`Sanción aplicada exitosamente a ${equipo.nombre}.`);
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-6">
      {/* Toast */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 bg-green-500/90 text-white px-5 py-3 rounded-2xl shadow-xl backdrop-blur-md flex items-center gap-2 text-sm font-semibold animate-in fade-in slide-in-from-bottom-5">
          <CheckCircle2 size={18} />
          {toastMsg}
        </div>
      )}

      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-xs text-white/30">
        <Link href="/admin/torneos" className="hover:text-white transition-colors">Torneos</Link>
        <span>/</span>
        <Link href={`/admin/torneos/${torneoId}`} className="hover:text-white transition-colors">{torneo.nombre}</Link>
        <span>/</span>
        <span className="text-white/60">Sanciones y Disciplina</span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">{torneo.juego.nombre}</span>
            <span className="text-white/20">•</span>
            <span className="text-xs text-white/40">{edicion.nombre}</span>
          </div>
          <h1 className="text-2xl font-black text-white flex items-center gap-2.5">
            <Flag className="text-rose-400" />
            Control Disciplinario y Sanciones
          </h1>
          <p className="text-sm text-white/40 mt-1">
            Registro público y vinculante de infracciones, penalizaciones y medidas disciplinarias.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-red-500/20"
        >
          <Plus size={16} />
          Aplicar Nueva Sanción
        </button>
      </div>

      {/* Sanciones List */}
      <div className="space-y-3">
        {sancionesList.length === 0 ? (
          <div className="bg-[#13131f] border border-white/8 rounded-2xl p-12 text-center text-white/30">
            <CheckCircle2 size={36} className="mx-auto mb-2 text-green-400 opacity-60" />
            <p className="text-sm font-semibold text-white/70">No hay sanciones registradas</p>
            <p className="text-xs text-white/40 mt-1">Todos los equipos mantienen su conducta deportiva limpia.</p>
          </div>
        ) : (
          sancionesList.map(s => {
            const badge = TIPO_BADGE[s.tipo];
            return (
              <div
                key={s.id}
                className="bg-[#13131f] border border-white/8 rounded-2xl p-5 hover:border-white/15 transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-3 border-b border-white/5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badge.color}`}>
                      {badge.icon}
                      {badge.label}
                    </span>
                    <span className="text-xs font-bold text-white">
                      {s.equipoNombre} {s.jugadorNick && <span className="text-violet-400 font-normal">({s.jugadorNick})</span>}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-white/30">
                    {s.fecha} • {s.aplicadoPor}
                  </span>
                </div>

                <div className="text-xs text-white/80 mb-2 leading-relaxed">
                  <span className="text-white/40 font-semibold">Motivo: </span>
                  {s.motivo}
                </div>

                <div className="flex items-center justify-between text-[11px] text-white/40 pt-1">
                  <span className="font-mono text-amber-300/80 bg-amber-500/10 px-2 py-0.5 rounded">
                    {s.articuloReglamento}
                  </span>
                  <span className="capitalize text-white/30">
                    Gravedad: <strong className={s.gravedad === 'grave' ? 'text-red-400' : 'text-amber-400'}>{s.gravedad}</strong>
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* New Sanction Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#13131f] border border-red-500/30 rounded-2xl max-w-lg w-full p-6 shadow-2xl animate-in zoom-in-95 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Flag className="text-red-400" size={20} />
              Aplicar Medida Disciplinaria
            </h3>

            <form onSubmit={handleCreateSanction} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-white/60 mb-1">Equipo Infractor</label>
                <select
                  value={selectedEquipoId}
                  onChange={(e) => setSelectedEquipoId(e.target.value)}
                  className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500"
                >
                  {MOCK_EQUIPOS.map(eq => (
                    <option key={eq.id} value={eq.id}>{eq.nombre} ({eq.tag})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-white/60 mb-1">Tipo de Medida</label>
                  <select
                    value={tipo}
                    onChange={(e) => setTipo(e.target.value as Sancion['tipo'])}
                    className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500"
                  >
                    <option value="advertencia">Advertencia Formal</option>
                    <option value="deduccion_puntos">Deducción de Puntos</option>
                    <option value="default_loss">Derrota por W.O.</option>
                    <option value="ban_jugador">Suspensión de Jugador</option>
                    <option value="descalificacion">Descalificación Completa</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-white/60 mb-1">Nivel de Gravedad</label>
                  <select
                    value={gravedad}
                    onChange={(e) => setGravedad(e.target.value as Sancion['gravedad'])}
                    className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500"
                  >
                    <option value="leve">Leve (1er aviso)</option>
                    <option value="moderada">Moderada</option>
                    <option value="grave">Grave (Reincidencia/Toxicidad)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-white/60 mb-1">Jugador Específico (Opcional)</label>
                <input
                  type="text"
                  value={jugadorNick}
                  onChange={(e) => setJugadorNick(e.target.value)}
                  placeholder="Ej. BeastMode#1002 (dejar vacío si es al squad entero)"
                  className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white/60 mb-1">Artículo del Reglamento Violado</label>
                <input
                  type="text"
                  value={articulo}
                  onChange={(e) => setArticulo(e.target.value)}
                  placeholder="Ej. Art. 5.2 - Uso de programas no autorizados o emuladores"
                  className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-white/60 mb-1">Descripción de los Hechos</label>
                <textarea
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  placeholder="Detalla lo sucedido durante el partido o sala..."
                  className="w-full bg-[#0e0e1a] border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-red-500 h-20 resize-none"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white/70 text-xs font-semibold rounded-xl"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-red-600/30"
                >
                  Confirmar Sanción
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
