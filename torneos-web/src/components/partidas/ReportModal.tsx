'use client';

import React, { useState } from 'react';
import { Partida } from '@/types';
import { X, Trophy, Upload, CheckCircle2, AlertTriangle, ShieldCheck, Camera, FileText } from 'lucide-react';

interface ReportModalProps {
  partida: Partida;
  onClose: () => void;
}

export default function ReportModal({ partida, onClose }: ReportModalProps) {
  const partA = partida.participaciones[0];
  const partB = partida.participaciones[1];

  const [scoreA, setScoreA] = useState<number>(partA?.mapasGanados ?? 0);
  const [scoreB, setScoreB] = useState<number>(partB?.mapasGanados ?? 0);
  const [evidencia, setEvidencia] = useState<string | null>(partida.evidenciaUrl ?? null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reportedSuccess, setReportedSuccess] = useState(false);
  const [showDisputeForm, setShowDisputeForm] = useState(false);
  const [motivoDisputa, setMotivoDisputa] = useState('');

  const handleSimulateUpload = () => {
    // Simula la subida de evidencia a Cloudflare R2
    setEvidencia('https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=800&auto=format&fit=crop');
  };

  const handleReport = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setReportedSuccess(true);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-fondo/80 backdrop-blur-md animate-in fade-in">
      <div className="w-full max-w-xl glass-card rounded-[6px] border border-borde-fuerte shadow-2xl overflow-hidden space-y-0">
        
        {/* Modal Header */}
        <div className="px-6 py-4 bg-fondo border-b border-borde flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Trophy className="w-5 h-5 text-acento-claro" />
            <div>
              <h3 className="font-extrabold text-sm text-white">Centro de Reporte de Partida</h3>
              <p className="text-[11px] text-tinta-3 font-mono">ID: #{partida.id} • BO{partida.formatoBo || 3}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-[4px] text-tinta-3 hover:text-white hover:bg-elevada transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stepper Status Bar */}
        <div className="bg-superficie/90 px-6 py-3 border-b border-borde flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${partida.estado === 'confirmada' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
            <span className="font-semibold text-tinta capitalize">Estado: {partida.estado.replace('_', ' ')}</span>
          </div>
          <span className="text-[11px] text-acento-claro font-mono bg-elevada/60 px-2 py-0.5 rounded border border-purple-800/40">
            Doble Confirmación de Capitanes
          </span>
        </div>

        {/* Body Content */}
        <div className="p-6 space-y-6">

          {reportedSuccess ? (
            <div className="text-center py-6 space-y-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-ok flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h4 className="font-extrabold text-base text-white">¡Resultado Reportado Exitosamente!</h4>
              <p className="text-xs text-tinta-3 max-w-md mx-auto">
                El marcador de <strong className="text-acento-claro">{scoreA} - {scoreB}</strong> ha sido enviado. El capitán rival tiene ventana para confirmar o abrir disputa.
              </p>
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-[6px] accion-principal text-white font-bold text-xs transition-all"
              >
                Cerrar Ventana
              </button>
            </div>
          ) : showDisputeForm ? (
            <div className="space-y-4">
              <div className="p-3 bg-amber-950/30 border border-amber-500/40 rounded-[6px] flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-atencion shrink-0 mt-0.5" />
                <div className="text-xs">
                  <h5 className="font-bold text-atencion">Abrir Disputa de Partida</h5>
                  <p className="text-tinta-3 text-[11px]">Un organizador o árbitro de staff revisará las capturas de pantalla de ambos capitanes.</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-tinta-2 mb-1">Motivo del Reclamo / Disputa</label>
                <textarea
                  rows={3}
                  value={motivoDisputa}
                  onChange={(e) => setMotivoDisputa(e.target.value)}
                  placeholder="Ej. El equipo rival usó un jugador no registrado en el roster o no asistió a la hora programada..."
                  className="w-full p-3 rounded-[6px] bg-fondo border border-borde text-xs text-tinta focus:outline-none focus:border-amber-500 transition-colors"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowDisputeForm(false)}
                  className="px-4 py-2 rounded-[6px] text-xs text-tinta-3 hover:text-white"
                >
                  Volver al Reporte
                </button>
                <button
                  onClick={() => { alert('Disputa enviada al Staff'); onClose(); }}
                  className="px-4 py-2 rounded-[6px] bg-amber-600 hover:bg-amber-500 text-fondo font-bold text-xs shadow-lg shadow-amber-600/20"
                >
                  Enviar Reclamo a Staff
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleReport} className="space-y-6">

              {/* Match Score Input */}
              <div className="grid grid-cols-2 gap-4 items-center bg-fondo/80 p-4 rounded-[6px] border border-borde">
                
                {/* Team A */}
                <div className="text-center space-y-2">
                  <span className="font-bold text-xs text-tinta block truncate">{partA?.equipo?.nombre || 'Equipo A'}</span>
                  <div className="flex items-center justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => setScoreA(Math.max(0, scoreA - 1))}
                      className="w-8 h-8 rounded-[4px] bg-elevada text-tinta-2 hover:bg-slate-700 font-bold"
                    >
                      -
                    </button>
                    <span className="font-mono text-2xl font-extrabold text-white w-8">{scoreA}</span>
                    <button
                      type="button"
                      onClick={() => setScoreA(scoreA + 1)}
                      className="w-8 h-8 rounded-[4px] bg-acento text-white hover:bg-acento-hover font-bold"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Team B */}
                <div className="text-center space-y-2 border-l border-borde">
                  <span className="font-bold text-xs text-tinta block truncate">{partB?.equipo?.nombre || 'Equipo B'}</span>
                  <div className="flex items-center justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => setScoreB(Math.max(0, scoreB - 1))}
                      className="w-8 h-8 rounded-[4px] bg-elevada text-tinta-2 hover:bg-slate-700 font-bold"
                    >
                      -
                    </button>
                    <span className="font-mono text-2xl font-extrabold text-white w-8">{scoreB}</span>
                    <button
                      type="button"
                      onClick={() => setScoreB(scoreB + 1)}
                      className="w-8 h-8 rounded-[4px] bg-acento text-white hover:bg-acento-hover font-bold"
                    >
                      +
                    </button>
                  </div>
                </div>

              </div>

              {/* Screenshot Evidence Upload */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-tinta-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Camera className="w-4 h-4 text-tinta-2" /> Captura de Pantalla / Evidencia (Requerido)</span>
                  <span className="text-[10px] text-tinta-4 font-mono">JPG, PNG (Max 5MB)</span>
                </label>

                {evidencia ? (
                  <div className="relative rounded-[6px] overflow-hidden border border-borde-fuerte group h-36 bg-superficie">
                    <img src={evidencia} alt="Evidencia de Victoria" className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-fondo/70 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-xs font-semibold text-ok flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" /> Screenshot Cargado
                      </span>
                      <button
                        type="button"
                        onClick={() => setEvidencia(null)}
                        className="px-2 py-1 bg-rose-600 text-white text-[10px] font-bold rounded"
                      >
                        Cambiar
                      </button>
                    </div>
                  </div>
                ) : (
                  <div
                    onClick={handleSimulateUpload}
                    className="border-2 border-dashed border-borde hover:border-acento/60 rounded-[6px] p-6 text-center cursor-pointer transition-colors bg-fondo/50 hover:bg-elevada/10 space-y-2"
                  >
                    <Upload className="w-6 h-6 text-acento-claro mx-auto" />
                    <p className="text-xs text-tinta-2 font-medium">Haz clic para adjuntar la captura del marcador final</p>
                    <p className="text-[10px] text-tinta-4">Obligatorio para la verificación del resultado por el rival</p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setShowDisputeForm(true)}
                  className="text-xs text-atencion hover:text-atencion flex items-center gap-1 font-medium"
                >
                  <AlertTriangle className="w-3.5 h-3.5" /> ¿Problemas? Abrir Disputa
                </button>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 rounded-[6px] text-xs text-tinta-3 hover:text-white"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || !evidencia}
                    className={`px-5 py-2.5 rounded-[6px] font-bold text-xs transition-all shadow-lg flex items-center gap-2 ${
                      evidencia
                        ? 'bg-acento text-white shadow-purple-600/25'
                        : 'bg-elevada text-tinta-4 cursor-not-allowed'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4" /> {isSubmitting ? 'Enviando...' : 'Enviar Resultado'}
                  </button>
                </div>
              </div>

            </form>
          )}

        </div>

      </div>
    </div>
  );
}
