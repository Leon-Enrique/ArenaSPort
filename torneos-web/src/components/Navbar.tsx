'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Trophy, LayoutDashboard, LogIn, ChevronDown, User, LogOut } from 'lucide-react';
import { Usuario } from '@/types';
import { api } from '@/lib/api';
import AuthModal from '@/components/AuthModal';
import NotificacionesBell from '@/components/NotificacionesBell';

const TOKEN_KEY = 'torneos_auth_token';

export default function Navbar() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return;
    api.setToken(token);
    api.getMe()
      .then(setUsuario)
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        api.setToken(null);
      });
  }, []);

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    api.setToken(null);
    setUsuario(null);
    setDropdownOpen(false);
  };

  return (
    <>
      <header className="sticky top-0 z-50 w-full glass-panel border-b border-borde-sutil">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">

          {/* El logo era un cuadrado con gradiente de tres colores y un
              texto con otro gradiente encima. Ahora la marca es la
              palabra; el cuadrado solo la ancla. */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-[22px] h-[22px] rounded-[3px] bg-acento flex items-center justify-center">
              <Trophy className="w-3 h-3 text-white" strokeWidth={2.5} />
            </div>
            <span className="text-sm font-bold tracking-wide text-tinta">
              ARENA <span className="text-tinta-3 font-medium">ESPORTS</span>
            </span>
          </Link>

          {/* Los íconos de colores distintos por ítem se van: un menú de
              navegación no necesita que cada entrada tenga su color. El
              texto alcanza, y deja el acento libre para marcar dónde
              estás parado. */}
          <nav className="hidden md:flex items-center gap-1 text-[13px]">
            <Link href="/" className="px-3.5 py-2 rounded-[4px] text-tinta-2 hover:text-tinta hover:bg-elevada transition-colors">
              Torneos
            </Link>

            <Link href="/equipos" className="px-3.5 py-2 rounded-[4px] text-tinta-2 hover:text-tinta hover:bg-elevada transition-colors">
              Equipos
            </Link>

            {usuario && (
              <Link href="/perfil" className="px-3.5 py-2 rounded-[4px] text-tinta-2 hover:text-tinta hover:bg-elevada transition-colors">
                Mi equipo
              </Link>
            )}

            {usuario?.rol === 'organizador' && (
              <Link href="/admin" className="ml-1 px-3.5 py-2 rounded-[4px] border border-borde text-tinta-2 hover:text-tinta hover:border-borde-fuerte transition-colors flex items-center gap-1.5">
                <LayoutDashboard className="w-3.5 h-3.5" /> Panel
              </Link>
            )}
          </nav>

          <div className="flex items-center gap-3">
            {usuario && <NotificacionesBell />}
            {usuario ? (
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2 hover:bg-elevada py-1.5 px-2 rounded-[4px] transition-colors"
                >
                  {usuario.avatarUrl ? (
                    <img src={usuario.avatarUrl} alt={usuario.nombre} className="w-[26px] h-[26px] rounded-[3px] object-cover" />
                  ) : (
                    <div className="w-[26px] h-[26px] rounded-[3px] bg-borde flex items-center justify-center text-[11px] font-semibold text-tinta-2">
                      {usuario.nombre.slice(0, 2).toUpperCase()}
                    </div>
                  )}
                  <span className="text-[13px] text-tinta-2 hidden sm:inline">{usuario.nombre}</span>
                  <ChevronDown className="w-3.5 h-3.5 text-tinta-4" />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-1.5 w-60 bg-elevada border border-borde rounded-[8px] py-1 z-50 elevacion filo">
                    <div className="px-3.5 py-2.5 border-b border-borde-sutil">
                      <p className="text-[13px] font-semibold text-tinta truncate">{usuario.nombre}</p>
                      <p className="text-[11px] text-tinta-3 mt-0.5 capitalize">{usuario.rol}</p>
                    </div>

                    {usuario.rol === 'organizador' ? (
                      <Link href="/admin" onClick={() => setDropdownOpen(false)} className="px-3.5 py-2 text-[13px] text-tinta-2 hover:bg-borde hover:text-tinta flex items-center gap-2.5 transition-colors">
                        <LayoutDashboard className="w-3.5 h-3.5 text-tinta-4" /> Panel de organizador
                      </Link>
                    ) : (
                      <Link href="/perfil" onClick={() => setDropdownOpen(false)} className="px-3.5 py-2 text-[13px] text-tinta-2 hover:bg-borde hover:text-tinta flex items-center gap-2.5 transition-colors">
                        <User className="w-3.5 h-3.5 text-tinta-4" /> Mi equipo y plantel
                      </Link>
                    )}

                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-3.5 py-2 text-[13px] text-tinta-3 hover:bg-borde hover:text-vivo flex items-center gap-2.5 transition-colors border-t border-borde-sutil mt-1"
                    >
                      <LogOut className="w-3.5 h-3.5" /> Cerrar sesión
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-[5px] accion-principal text-white font-semibold text-[13px]"
              >
                <LogIn className="w-3.5 h-3.5" /> Iniciar sesión
              </button>
            )}
          </div>

        </div>
      </header>

      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onLoggedIn={setUsuario}
      />
    </>
  );
}
