'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Shield, Trophy, LayoutDashboard, LogIn, ChevronDown, User, LogOut, Sparkles } from 'lucide-react';
import { Usuario } from '@/types';
import { api } from '@/lib/api';
import AuthModal from '@/components/AuthModal';

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
      <header className="sticky top-0 z-50 w-full glass-panel border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">

          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 p-0.5 shadow-lg shadow-purple-500/20 group-hover:scale-105 transition-transform">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Trophy className="w-5 h-5 text-purple-400 group-hover:text-cyan-300 transition-colors" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="font-extrabold text-lg tracking-wider bg-gradient-to-r from-white via-slate-200 to-purple-300 bg-clip-text text-transparent">
                ARENA<span className="text-purple-500">ESPORTS</span>
              </span>
              <span className="text-[10px] text-cyan-400 font-semibold tracking-widest uppercase -mt-1 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> Mobile League
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
            <Link href="/" className="px-3.5 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 transition-all flex items-center gap-2">
              <Trophy className="w-4 h-4 text-purple-400" /> Torneos
            </Link>

            {usuario?.rol === 'organizador' ? (
              <Link href="/admin" className="px-3.5 py-2 rounded-lg bg-purple-950/60 text-purple-300 border border-purple-700/60 hover:bg-purple-900/60 transition-all flex items-center gap-2 ml-2 shadow-md">
                <LayoutDashboard className="w-4 h-4 text-purple-400" /> Panel Admin
              </Link>
            ) : usuario && (
              <Link href="/perfil" className="px-3.5 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 transition-all flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-400" /> Mi Equipo
              </Link>
            )}
          </nav>

          <div className="flex items-center gap-3">
            {usuario ? (
              <div className="relative">
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2.5 bg-slate-900/80 border border-slate-800 hover:border-purple-500/50 p-1.5 pr-3 rounded-full transition-all"
                >
                  {usuario.avatarUrl ? (
                    <img src={usuario.avatarUrl} alt={usuario.nombre} className="w-8 h-8 rounded-full object-cover border border-purple-500/40" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-purple-950 border border-purple-500/40 flex items-center justify-center">
                      <User className="w-4 h-4 text-purple-300" />
                    </div>
                  )}
                  <span className="text-xs font-semibold text-slate-200 hidden sm:inline">{usuario.nombre}</span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-64 glass-card rounded-2xl shadow-2xl border border-slate-800 py-2 z-50 bg-[#0e101a]">
                    <div className="px-4 py-2 border-b border-slate-800">
                      <p className="text-xs text-slate-400">Conectado como</p>
                      <p className="text-sm font-semibold text-white truncate">{usuario.nombre}</p>
                      <span className={`inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        usuario.rol === 'organizador'
                          ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      }`}>
                        {usuario.rol}
                      </span>
                    </div>

                    {usuario.rol === 'organizador' ? (
                      <Link href="/admin" onClick={() => setDropdownOpen(false)} className="px-4 py-2.5 text-xs text-purple-300 hover:bg-slate-800/80 flex items-center gap-2 transition-colors">
                        <LayoutDashboard className="w-4 h-4 text-purple-400" /> Panel Organizador
                      </Link>
                    ) : (
                      <Link href="/perfil" onClick={() => setDropdownOpen(false)} className="px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-800/80 flex items-center gap-2 transition-colors">
                        <User className="w-4 h-4 text-purple-400" /> Mi Equipo y Roster
                      </Link>
                    )}

                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-xs text-rose-400 hover:bg-rose-950/30 flex items-center gap-2 transition-colors border-t border-slate-800/60 mt-1"
                    >
                      <LogOut className="w-3.5 h-3.5" /> Cerrar Sesión
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => setAuthModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs transition-all shadow-lg shadow-purple-600/30"
              >
                <LogIn className="w-4 h-4" /> Iniciar Sesión
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
