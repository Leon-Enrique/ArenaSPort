'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api } from '@/lib/api';
import { Edicion } from '@/types';
import {
  Trophy, Users, ChevronRight, CheckCircle2, Loader2, PlusCircle
} from 'lucide-react';

const ESTADO_LABEL: Record<string, string> = {
  inscripciones_abiertas: 'Inscripciones Abiertas',
  en_curso: 'En Curso',
  finalizada: 'Finalizado',
};

/**
 * La tarjeta de un torneo.
 *
 * La primera versión de este rediseño se pasó de sobria: quitar los
 * gradientes dejó una tarjeta con dos datos y mucho aire, que se lee
 * barata por vacía. Lo que hace que una plataforma se vea seria no es la
 * falta de adorno, es la DENSIDAD: cuánta información útil entra sin que
 * se vuelva ruido.
 *
 * Así que cada estado muestra lo que de verdad importa en ese momento:
 *
 *   - Inscripciones abiertas → cuántos cupos quedan, con barra. Es el dato
 *     que decide si te anotás hoy o mañana.
 *   - En vivo → que está pasando ahora, en rojo y sin animación de borde.
 *   - Terminado → el premio y el tamaño, que es lo que queda de historia.
 */
function mostrarTorneo(edicion: Edicion): boolean {
  const torneo = (edicion.torneoNombre || '').trim();
  const nombre = (edicion.nombre || '').trim();
  if (!torneo || torneo === nombre) return false;
  const a = torneo.toLowerCase();
  const b = nombre.toLowerCase();
  return !a.includes(b) && !b.includes(a);
}

function TarjetaTorneo({ edicion }: { edicion: Edicion }) {
  const enVivo = edicion.estado === 'en_curso';
  const abierto = edicion.estado === 'inscripciones_abiertas';

  const cupos = edicion.maxEquipos || 0;
  const inscritos = edicion.equiposInscritosCount;
  const llenado = cupos > 0 ? Math.min(100, Math.round((inscritos / cupos) * 100)) : 0;

  const acento = enVivo ? 'bg-vivo' : abierto ? 'bg-ok' : 'bg-borde-fuerte';

  return (
    <Link
      href={`/torneos/${edicion.slug}`}
      className="group glass-card overflow-hidden flex flex-col hover:-translate-y-px"
    >
      <div className={`h-[3px] ${acento}`} />

      <div className="p-5 flex flex-col gap-4 flex-1">
        {/* Identidad: la marca del juego como ancla visual. Un cuadrado
            de 34px con la sigla pesa más que un banner vacío de 128px. */}
        <div className="flex items-start gap-3">
          <div className="w-[34px] h-[34px] rounded-[5px] bg-elevada border border-borde flex items-center justify-center shrink-0 filo">
            <span className="font-mono text-[10px] font-semibold text-tinta-2 tracking-tight">
              {edicion.juego.codigo.slice(0, 4).toUpperCase()}
            </span>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] mb-1">
              {enVivo ? (
                <span className="flex items-center gap-1.5 text-vivo">
                  <span className="w-[5px] h-[5px] rounded-full bg-vivo punto-vivo" />
                  En vivo
                </span>
              ) : (
                <span className={abierto ? 'text-ok' : 'text-tinta-4'}>
                  {abierto ? 'Inscripciones abiertas' : 'Terminado'}
                </span>
              )}
            </div>
            <h3 className="font-semibold text-[16.5px] tracking-[-0.02em] text-tinta leading-[1.25] group-hover:text-white transition-colors">
              {edicion.nombre}
            </h3>
            {/* El nombre del torneo solo si aporta jerarquía real
                ("2da Edición" ← "Copa Santa Cruz"). Cuando uno contiene al
                otro es la misma cosa escrita dos veces, y repetirla es el
                relleno que hace que una tarjeta se vea generada. */}
            {mostrarTorneo(edicion) && (
              <p className="text-[12px] text-tinta-4 mt-0.5 truncate">{edicion.torneoNombre}</p>
            )}
          </div>
        </div>

        {/* Cupos con barra: sirve para los tres estados, pero solo en
            "abierto" es una decisión — ahí se dice cuánto falta. */}
        <div className="mt-auto">
          <div className="flex items-baseline justify-between mb-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-tinta-3">
              Equipos
            </span>
            <span className="font-mono tabular text-[13px] text-tinta">
              {inscritos}
              {cupos > 0 && <span className="text-tinta-4">/{cupos}</span>}
            </span>
          </div>
          <div className="h-[3px] rounded-full bg-borde-sutil overflow-hidden">
            <div
              className={`h-full rounded-full ${abierto ? 'bg-ok' : enVivo ? 'bg-vivo' : 'bg-borde-fuerte'}`}
              style={{ width: `${llenado}%` }}
            />
          </div>
          {abierto && cupos > 0 && (
            <p className="text-[11.5px] text-tinta-3 mt-1.5">
              {cupos - inscritos > 0
                ? `Quedan ${cupos - inscritos} cupos`
                : 'Cupos llenos'}
            </p>
          )}
        </div>

        {/* Pie: premio a la izquierda con peso real, acción a la derecha. */}
        <div className="flex items-end justify-between gap-3 pt-3.5 border-t border-borde-sutil">
          <div>
            <div className="text-[9px] font-semibold uppercase tracking-[0.08em] text-tinta-3 mb-0.5">
              {edicion.bolsaPremios ? 'Premio' : 'Inicio'}
            </div>
            <div className="font-mono tabular text-[15px] font-semibold text-tinta leading-none">
              {edicion.bolsaPremios ||
                (edicion.fechaInicio
                  ? new Date(edicion.fechaInicio).toLocaleDateString('es-BO', { day: '2-digit', month: '2-digit' })
                  : '—')}
            </div>
          </div>
          <span className="text-[12.5px] font-semibold text-acento-claro flex items-center gap-0.5 group-hover:gap-1.5 transition-all">
            Ver torneo <ChevronRight className="w-3.5 h-3.5" />
          </span>
        </div>
      </div>
    </Link>
  );
}

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

  const enVivo = ediciones.find(e => e.estado === 'en_curso');
  const torneosActivos = ediciones.filter(e => e.estado === 'en_curso' || e.estado === 'inscripciones_abiertas').length;
  const equiposTotales = ediciones.reduce((acc, e) => acc + e.equiposInscritosCount, 0);

  return (
    <div className="min-h-screen flex flex-col bg-fondo text-tinta selection:bg-acento selection:text-white">
      <Navbar />

      <main className="flex-1 space-y-14 pb-20">
        {/* Portada.
            Antes: un halo de gradiente de 800×400 con blur de 140px, un
            título con gradiente de tres colores y una píldora "Plataforma
            Profesional". Nada de eso decía qué hay adentro.
            Ahora la portada dice el estado real de la liga — y si hay algo
            en vivo, eso es lo que importa. */}
        <section className="border-b border-borde-sutil">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-14">
            <div className="max-w-2xl">
              <h1 className="text-[34px] sm:text-[42px] font-bold tracking-[-0.03em] text-tinta leading-[1.08]">
                Torneos de Mobile Legends<br className="hidden sm:inline" /> en Bolivia
              </h1>
              <p className="mt-3 text-[14px] sm:text-[15px] text-tinta-3 leading-relaxed max-w-xl">
                Inscribí a tu equipo, seguí el cuadro en vivo y reportá tus
                resultados. Sin planillas ni grupos de WhatsApp.
              </p>

              {!loading && !error && (
                <div className="flex items-center gap-8 mt-8">
                  <div>
                    <div className="font-mono tabular text-[28px] font-semibold text-tinta leading-none">{torneosActivos}</div>
                    <div className="text-[10px] text-tinta-3 uppercase tracking-[0.08em] font-semibold mt-1.5">Torneos activos</div>
                  </div>
                  <div className="w-px h-9 bg-borde" />
                  <div>
                    <div className="font-mono tabular text-[28px] font-semibold text-tinta leading-none">{equiposTotales}</div>
                    <div className="text-[10px] text-tinta-3 uppercase tracking-[0.08em] font-semibold mt-1.5">Equipos inscritos</div>
                  </div>
                </div>
              )}
            </div>

            {/* Si hay algo jugándose ahora, esa es la noticia — y ocupa el
                espacio que antes era una franja negra vacía. */}
            {enVivo && (
              <Link
                href={`/torneos/${enVivo.slug}`}
                className="glass-card estado-vivo mt-9 flex flex-wrap items-center gap-x-6 gap-y-3 px-5 py-4 group"
              >
                <div className="flex items-center gap-2 shrink-0">
                  <span className="w-[6px] h-[6px] rounded-full bg-vivo punto-vivo" />
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-vivo">
                    Jugándose ahora
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-[16px] tracking-[-0.02em] text-tinta truncate">
                    {enVivo.nombre}
                  </div>
                  <div className="text-[12.5px] text-tinta-3 mt-0.5">
                    {enVivo.equiposInscritosCount} equipos · {enVivo.juego.nombre}
                  </div>
                </div>
                {enVivo.bolsaPremios && (
                  <div className="text-right shrink-0">
                    <div className="font-mono tabular text-[17px] font-semibold text-tinta leading-none">
                      {enVivo.bolsaPremios}
                    </div>
                    <div className="text-[9px] font-semibold uppercase tracking-[0.08em] text-tinta-3 mt-1">
                      Premio
                    </div>
                  </div>
                )}
                <span className="text-[12.5px] font-semibold text-acento-claro flex items-center gap-0.5 group-hover:gap-1.5 transition-all shrink-0">
                  Ver cuadro <ChevronRight className="w-3.5 h-3.5" />
                </span>
              </Link>
            )}
          </div>
        </section>

        {/* TOURNAMENTS EXPLORER */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h2 className="text-[22px] font-bold tracking-[-0.025em] text-tinta">
                Torneos
              </h2>
              <p className="text-[13px] text-tinta-3 mt-1">
                {ediciones.length} {ediciones.length === 1 ? 'torneo' : 'torneos'}
                {torneosActivos > 0 && ` · ${torneosActivos} ${torneosActivos === 1 ? 'activo' : 'activos'}`}
              </p>
            </div>

            {juegosDisponibles.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                {/* Un solo juego activo no es una elección: el selector
                    solo aparece cuando hay algo que elegir. */}
                {juegosDisponibles.length > 1 && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setSelectedJuego('todos')}
                      className={`px-2.5 py-1.5 rounded-[4px] text-[12px] font-medium transition-colors ${selectedJuego === 'todos' ? 'bg-borde text-tinta' : 'text-tinta-3 hover:text-tinta'}`}
                    >
                      Todos
                    </button>
                    {juegosDisponibles.map((j) => (
                      <button
                        key={j.id}
                        onClick={() => setSelectedJuego(j.codigo)}
                        className={`px-2.5 py-1.5 rounded-[4px] text-[12px] font-medium transition-colors ${selectedJuego === j.codigo ? 'bg-borde text-tinta' : 'text-tinta-3 hover:text-tinta'}`}
                      >
                        {j.codigo.toUpperCase()}
                      </button>
                    ))}
                  </div>
                )}

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setStatusFilter('todos')}
                    className={`px-2.5 py-1.5 rounded-[4px] text-[12px] font-medium transition-colors ${statusFilter === 'todos' ? 'bg-borde text-tinta' : 'text-tinta-3 hover:text-tinta'}`}
                  >
                    Todos
                  </button>
                  <button
                    onClick={() => setStatusFilter('en_curso')}
                    className={`px-2.5 py-1.5 rounded-[4px] text-[12px] font-medium transition-colors ${statusFilter === 'en_curso' ? 'bg-borde text-tinta' : 'text-tinta-3 hover:text-tinta'}`}
                  >
                    En vivo
                  </button>
                  <button
                    onClick={() => setStatusFilter('inscripciones_abiertas')}
                    className={`px-2.5 py-1.5 rounded-[4px] text-[12px] font-medium transition-colors ${statusFilter === 'inscripciones_abiertas' ? 'bg-borde text-tinta' : 'text-tinta-3 hover:text-tinta'}`}
                  >
                    Inscripciones
                  </button>
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center gap-2 text-tinta-3 text-sm py-20">
              <Loader2 className="animate-spin" size={18} /> Cargando torneos...
            </div>
          ) : error ? (
            <div className="bg-superficie border border-vivo/25 estado-vivo rounded-[8px] p-10 text-center text-[13px] text-tinta-2">
              No pudimos conectar con el servidor. Verificá que el backend esté corriendo en <code className="text-tinta-2">localhost:8000</code>.
            </div>
          ) : filteredEdiciones.length === 0 ? (
            <div className="glass-card p-12 text-center space-y-3">
              <PlusCircle className="w-8 h-8 text-tinta-4 mx-auto" />
              <p className="text-sm text-tinta-3">
                {ediciones.length === 0 ? 'Todavía no hay torneos publicados.' : 'Ningún torneo coincide con el filtro elegido.'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredEdiciones.map((edicion) => (
                /* La cabecera decorativa de 128px se fue: era un gradiente
                   con un ícono al 10% de opacidad, o sea 128px que no
                   decían nada. Ahora el estado vive en 3px de franja y
                   esos pixeles son datos. */
                <TarjetaTorneo key={edicion.id} edicion={edicion} />
              ))}
            </div>
          )}
        </section>

        {/* HOW TO COMPETE SECTION */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-card p-8 sm:p-12 space-y-10">
            <div className="text-center max-w-2xl mx-auto space-y-2">
              <h2 className="text-[22px] sm:text-[26px] font-bold text-tinta">¿Cómo Participar en Nuestros Torneos?</h2>
              <p className="text-xs sm:text-sm text-tinta-3">Sigue 3 pasos sencillos desde la inscripción hasta la coronación de campeones.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {[
                { step: '01', title: 'Inscríbete', desc: 'Registra a tu equipo con sus Game IDs oficiales en el torneo que quieras.', icon: <Users className="text-tinta-2" size={20} /> },
                { step: '02', title: 'Espera tu Cuadro', desc: 'Cuando cierran las inscripciones, el organizador sortea las llaves.', icon: <CheckCircle2 className="text-tinta-2" size={20} /> },
                { step: '03', title: 'Compite y Gana', desc: 'Jugá tus partidas siguiendo el bracket y sumá puntos para el premio.', icon: <Trophy className="text-ok" size={20} /> },
              ].map((item, idx) => (
                <div key={idx} className="p-6 rounded-[6px] bg-hundida border border-borde-sutil space-y-3 relative group hover:border-borde transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-[6px] bg-elevada border border-borde-sutil flex items-center justify-center">
                      {item.icon}
                    </div>
                    <span className="font-mono tabular text-[18px] font-semibold text-tinta-4 group-hover:text-tinta-3 transition-colors">
                      {item.step}
                    </span>
                  </div>
                  <h3 className="font-bold text-sm text-white">{item.title}</h3>
                  <p className="text-xs text-tinta-3 leading-relaxed">{item.desc}</p>
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
