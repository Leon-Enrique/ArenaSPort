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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in">
      <div className="w-full max-w-xl glass-card rounded-2xl border border-slate-700 shadow-2xl overflow-hidden space-y-0">
        
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Trophy className="w-5 h-5 text-purple-400" />
            <div>
              <h3 className="font-extrabold text-sm text-white">Centro de Reporte de Partida</h3>
              <p className="text-[11px] text-slate-400 font-mono">ID: #{partida.id} • BO{partida.formatoBo || 3}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stepper Status Bar */}
        <div className="bg-slate-900/90 px-6 py-3 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${partida.estado === 'confirmada' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
            <span className="font-semibold text-slate-200 capitalize">Estado: {partida.estado.replace('_', ' ')}</span>
          </div>
          <span className="text-[11px] text-purple-300 font-mono bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">
            Doble Confirmación de Capitanes
          </span>
        </div>

        {/* Body Content */}
        <div className="p-6 space-y-6">

          {reportedSuccess ? (
            <div className="text-center py-6 space-y-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h4 className="font-extrabold text-base text-white">¡Resultado Reportado Exitosamente!</h4>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                El marcador de <strong className="text-purple-300">{scoreA} - {scoreB}</strong> ha sido enviado. El capitán rival tiene ventana para confirmar o abrir disputa.
              </p>
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs transition-all shadow-lg shadow-purple-600/30"
              >
                Cerrar Ventana
              </button>
            </div>
          ) : showDisputeForm ? (
            <div className="space-y-4">
              <div className="p-3 bg-amber-950/30 border border-amber-500/40 rounded-xl flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <h5 className="font-bold text-amber-300">Abrir Disputa de Partida</h5>
                  <p className="text-slate-400 text-[11px]">Un organizador o árbitro de staff revisará las capturas de pantalla de ambos capitanes.</p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Motivo del Reclamo / Disputa</label>
                <textarea
                  rows={3}
                  value={motivoDisputa}
                  onChange={(e) => setMotivoDisputa(e.target.value)}
                  placeholder="Ej. El equipo rival usó un jugador no registrado en el roster o no asistió a la hora programada..."
                  className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-amber-500 transition-colors"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setShowDisputeForm(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                >
                  Volver al Reporte
                </button>
                <button
                  onClick={() => { alert('Disputa enviada al Staff'); onClose(); }}
                  className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs shadow-lg shadow-amber-600/20"
                >
                  Enviar Reclamo a Staff
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleReport} className="space-y-6">

              {/* Match Score Input */}
              <div className="grid grid-cols-2 gap-4 items-center bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                
                {/* Team A */}
                <div className="text-center space-y-2">
                  <span className="font-bold text-xs text-slate-200 block truncate">{partA?.equipo?.nombre || 'Equipo A'}</span>
                  <div className="flex items-center justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => setScoreA(Math.max(0, scoreA - 1))}
                      className="w-8 h-8 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-bold"
                    >
                      -
                    </button>
                    <span className="font-mono text-2xl font-extrabold text-white w-8">{scoreA}</span>
                    <button
                      type="button"
                      onClick={() => setScoreA(scoreA + 1)}
                      className="w-8 h-8 rounded-lg bg-purple-600 text-white hover:bg-purple-500 font-bold"
                    >
                      +
                    </button>
                  </div>
                </div>

                {/* Team B */}
                <div className="text-center space-y-2 border-l border-slate-800">
                  <span className="font-bold text-xs text-slate-200 block truncate">{partB?.equipo?.nombre || 'Equipo B'}</span>
                  <div className="flex items-center justify-center gap-2">
                    <button
                      type="button"
                      onClick={() => setScoreB(Math.max(0, scoreB - 1))}
                      className="w-8 h-8 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-bold"
                    >
                      -
                    </button>
                    <span className="font-mono text-2xl font-extrabold text-white w-8">{scoreB}</span>
                    <button
                      type="button"
                      onClick={() => setScoreB(scoreB + 1)}
                      className="w-8 h-8 rounded-lg bg-purple-600 text-white hover:bg-purple-500 font-bold"
                    >
                      +
                    </button>
                  </div>
                </div>

              </div>

              {/* Screenshot Evidence Upload */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span className="flex items-center gap-1.5"><Camera className="w-4 h-4 text-cyan-400" /> Captura de Pantalla / Evidencia (Requerido)</span>
                  <span className="text-[10px] text-slate-500 font-mono">JPG, PNG (Max 5MB)</span>
                </label>

                {evidencia ? (
                  <div className="relative rounded-xl overflow-hidden border border-slate-700 group h-36 bg-slate-900">
                    <img src={evidencia} alt="Evidencia de Victoria" className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-slate-950/70 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
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
                    className="border-2 border-dashed border-slate-800 hover:border-purple-500/60 rounded-xl p-6 text-center cursor-pointer transition-colors bg-slate-950/50 hover:bg-purple-950/10 space-y-2"
                  >
                    <Upload className="w-6 h-6 text-purple-400 mx-auto" />
                    <p className="text-xs text-slate-300 font-medium">Haz clic para adjuntar la captura del marcador final</p>
                    <p className="text-[10px] text-slate-500">Obligatorio para la verificación del resultado por el rival</p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => setShowDisputeForm(true)}
                  className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 font-medium"
                >
                  <AlertTriangle className="w-3.5 h-3.5" /> ¿Problemas? Abrir Disputa
                </button>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting || !evidencia}
                    className={`px-5 py-2.5 rounded-xl font-bold text-xs transition-all shadow-lg flex items-center gap-2 ${
                      evidencia
                        ? 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-purple-600/25'
                        : 'bg-slate-800 text-slate-500 cursor-not-allowed'
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
