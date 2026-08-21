'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api } from '@/lib/api';
import { Edicion } from '@/types';
import {
  Trophy, Users, Sparkles, Calendar, Award,
  ChevronRight, Gamepad2, CheckCircle2, Clock, Loader2, PlusCircle
} from 'lucide-react';

const ESTADO_LABEL: Record<string, string> = {
  inscripciones_abiertas: 'Inscripciones Abiertas',
  en_curso: 'En Curso',
  finalizada: 'Finalizado',
};

export default function Home() {
  const [selectedJuego, setSelectedJuego] = useState<string>('todos');
  const [statusFilter, setStatusFilter] = useState<'todos' | 'en_curso' | 'inscripciones_abiertas'>('todos');
  const [ediciones, setEdiciones] = useState<Edicion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let activo = true;
    api.getEdicionesCompletas()
      .then(data => activo && setEdiciones(data))
      .catch(() => activo && setError(true))
      .finally(() => activo && setLoading(false));
    return () => { activo = false; };
  }, []);

  const juegosDisponibles = Array.from(new Map(ediciones.map(e => [e.juego.codigo, e.juego])).values());

  const filteredEdiciones = ediciones.filter(e => {
    const matchJuego = selectedJuego === 'todos' || e.juego.codigo === selectedJuego;
    const matchStatus = statusFilter === 'todos' || e.estado === statusFilter;
    return matchJuego && matchStatus;
  });

  const torneosActivos = ediciones.filter(e => e.estado === 'en_curso' || e.estado === 'inscripciones_abiertas').length;
  const equiposTotales = ediciones.reduce((acc, e) => acc + e.equiposInscritosCount, 0);

  return (
    <div className="min-h-screen flex flex-col bg-[#080811] text-slate-100 selection:bg-violet-600 selection:text-white">
      <Navbar />

      <main className="flex-1 space-y-20 pb-24">
        {/* HERO SECTION */}
        <section className="relative overflow-hidden pt-10 pb-16">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-gradient-to-tr from-violet-600/25 via-indigo-600/20 to-cyan-500/20 blur-[140px] rounded-full pointer-events-none" />

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center space-y-6">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-violet-950/70 border border-violet-500/40 text-xs font-semibold text-violet-300 shadow-inner">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> Plataforma Profesional de Esports Móviles
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-tight">
                COMPITE EN LAS LIGAS DE <br className="hidden sm:inline" />
                <span className="bg-gradient-to-r from-violet-400 via-cyan-300 to-amber-300 bg-clip-text text-transparent">
                  ESPORTS DE LATINOAMÉRICA
                </span>
              </h1>

              <p className="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">
                Inscribe a tu escuadra en torneos oficiales con cuadro de llaves en vivo, control de árbitros y premios garantizados.
              </p>

              {!loading && !error && (
                <div className="grid grid-cols-2 gap-4 pt-4 max-w-sm mx-auto">
                  <div>
                    <span className="font-mono text-2xl sm:text-3xl font-black text-white block">{torneosActivos}</span>
                    <span className="text-[11px] text-white/40 uppercase tracking-wider font-semibold">Torneos Activos</span>
                  </div>
                  <div>
                    <span className="font-mono text-2xl sm:text-3xl font-black text-violet-400 block">{equiposTotales}</span>
                    <span className="text-[11px] text-white/40 uppercase tracking-wider font-semibold">Equipos Inscritos</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* TOURNAMENTS EXPLORER */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-white/8 pb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold text-violet-400 uppercase tracking-wider">Explorador Oficial</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white flex items-center gap-2.5">
                <Gamepad2 className="text-violet-400" /> Torneos y Temporadas
              </h2>
            </div>

            {juegosDisponibles.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center bg-[#131322] p-1 rounded-xl border border-white/10">
                  <button
                    onClick={() => setSelectedJuego('todos')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${selectedJuego === 'todos' ? 'bg-violet-600 text-white shadow-md' : 'text-white/40 hover:text-white'}`}
                  >
                    Todos
                  </button>
                  {juegosDisponibles.map((j) => (
                    <button
                      key={j.id}
                      onClick={() => setSelectedJuego(j.codigo)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${selectedJuego === j.codigo ? 'bg-violet-600 text-white shadow-md' : 'text-white/40 hover:text-white'}`}
                    >
                      {j.codigo.toUpperCase()}
                    </button>
                  ))}
                </div>

                <div className="flex items-center bg-[#131322] p-1 rounded-xl border border-white/10">
                  <button
                    onClick={() => setStatusFilter('todos')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${statusFilter === 'todos' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white'}`}
                  >
                    Todos
                  </button>
                  <button
                    onClick={() => setStatusFilter('en_curso')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${statusFilter === 'en_curso' ? 'bg-emerald-500/20 text-emerald-300 font-bold' : 'text-white/40 hover:text-white'}`}
                  >
                    En Curso
                  </button>
                  <button
                    onClick={() => setStatusFilter('inscripciones_abiertas')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${statusFilter === 'inscripciones_abiertas' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-white/40 hover:text-white'}`}
                  >
                    Inscripciones Abiertas
                  </button>
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center gap-2 text-white/40 text-sm py-20">
              <Loader2 className="animate-spin" size={18} /> Cargando torneos...
            </div>
          ) : error ? (
            <div className="bg-[#11111f] border border-rose-500/20 rounded-3xl p-10 text-center text-sm text-white/50">
              No pudimos conectar con el servidor. Verificá que el backend esté corriendo en <code className="text-cyan-400">localhost:8000</code>.
            </div>
          ) : filteredEdiciones.length === 0 ? (
            <div className="bg-[#11111f] border border-white/8 rounded-3xl p-12 text-center space-y-3">
              <PlusCircle className="w-8 h-8 text-white/20 mx-auto" />
              <p className="text-sm text-white/50">
                {ediciones.length === 0 ? 'Todavía no hay torneos publicados.' : 'Ningún torneo coincide con el filtro elegido.'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredEdiciones.map((edicion) => (
                <div
                  key={edicion.id}
                  className="bg-[#11111f] rounded-3xl overflow-hidden border border-white/8 flex flex-col justify-between group hover:border-violet-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-violet-500/10"
                >
                  <div className="relative h-32 overflow-hidden bg-gradient-to-br from-violet-950 to-slate-950 flex items-center justify-center">
                    <Gamepad2 className="w-10 h-10 text-white/10" />
                    <div className="absolute top-3.5 left-3.5 flex items-center gap-2">
                      <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase bg-violet-950/90 border border-violet-500 text-violet-300 backdrop-blur-md">
                        {edicion.juego.nombre}
                      </span>
                      {(edicion.estado === 'en_curso' || edicion.estado === 'inscripciones_abiertas') && (
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase backdrop-blur-md ${
                          edicion.estado === 'en_curso' ? 'bg-emerald-950/90 border border-emerald-500 text-emerald-300' : 'bg-cyan-950/90 border border-cyan-500 text-cyan-300'
                        }`}>
                          {ESTADO_LABEL[edicion.estado]}
                        </span>
                      )}
                    </div>
                    {edicion.bolsaPremios && (
                      <div className="absolute bottom-3 right-3.5 bg-amber-500/20 backdrop-blur-md border border-amber-500/40 px-3.5 py-1 rounded-xl text-amber-300 font-mono font-black text-xs flex items-center gap-1.5">
                        <Award className="w-3.5 h-3.5 text-amber-400" /> {edicion.bolsaPremios}
                      </div>
                    )}
                  </div>

                  <div className="p-6 space-y-4 flex-1 flex flex-col justify-between">
                    <div className="space-y-2">
                      <h3 className="font-extrabold text-base text-white group-hover:text-violet-300 transition-colors leading-snug">
                        {edicion.nombre}
                      </h3>
                    </div>

                    <div className="space-y-2.5 pt-4 border-t border-white/5 text-xs">
                      <div className="flex items-center justify-between text-white/80">
                        <span className="flex items-center gap-1.5 text-white/40">
                          <Users className="w-3.5 h-3.5 text-violet-400" /> Equipos:
                        </span>
                        <span className="font-mono font-bold text-white">
                          {edicion.equiposInscritosCount}{edicion.maxEquipos ? ` / ${edicion.maxEquipos}` : ''}
                        </span>
                      </div>
                      {edicion.fechaInicio && (
                        <div className="flex items-center justify-between text-white/80">
                          <span className="flex items-center gap-1.5 text-white/40">
                            <Calendar className="w-3.5 h-3.5 text-cyan-400" /> Inicio:
                          </span>
                          <span className="font-mono font-semibold text-white/70">
                            {new Date(edicion.fechaInicio).toLocaleDateString('es-BO')}
                          </span>
                        </div>
                      )}
                    </div>

                    <Link
                      href={`/torneos/${edicion.slug}`}
                      className="w-full mt-4 py-3 rounded-xl bg-[#16162a] group-hover:bg-gradient-to-r group-hover:from-violet-600 group-hover:to-cyan-600 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all border border-white/8 group-hover:border-transparent shadow-lg"
                    >
                      Ver Torneo <ChevronRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* HOW TO COMPETE SECTION */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-[#11111f] rounded-3xl p-8 sm:p-12 border border-white/8 space-y-10">
            <div className="text-center max-w-2xl mx-auto space-y-2">
              <h2 className="text-2xl sm:text-3xl font-black text-white">¿Cómo Participar en Nuestros Torneos?</h2>
              <p className="text-xs sm:text-sm text-white/40">Sigue 3 pasos sencillos desde la inscripción hasta la coronación de campeones.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {[
                { step: '01', title: 'Inscríbete', desc: 'Registra a tu equipo con sus Game IDs oficiales en el torneo que quieras.', icon: <Users className="text-violet-400" size={20} /> },
                { step: '02', title: 'Espera tu Cuadro', desc: 'Cuando cierran las inscripciones, el organizador sortea las llaves.', icon: <CheckCircle2 className="text-cyan-400" size={20} /> },
                { step: '03', title: 'Compite y Gana', desc: 'Jugá tus partidas siguiendo el bracket y sumá puntos para el premio.', icon: <Trophy className="text-green-400" size={20} /> },
              ].map((item, idx) => (
                <div key={idx} className="p-6 rounded-2xl bg-[#0b0b14] border border-white/5 space-y-3 relative group hover:border-violet-500/30 transition-all">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
                      {item.icon}
                    </div>
                    <span className="font-mono text-xl font-black text-white/20 group-hover:text-violet-400 transition-colors">
                      {item.step}
                    </span>
                  </div>
                  <h3 className="font-bold text-sm text-white">{item.title}</h3>
                  <p className="text-xs text-white/40 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
