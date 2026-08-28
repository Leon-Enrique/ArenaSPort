'use client';

import React, { useState } from 'react';
import { Sparkles, X, Mail, Lock, User, AlertCircle, Loader2 } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import { Usuario } from '@/types';

const TOKEN_KEY = 'torneos_auth_token';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoggedIn: (usuario: Usuario) => void;
}

export default function AuthModal({ isOpen, onClose, onLoggedIn }: AuthModalProps) {
  const [tab, setTab] = useState<'login' | 'registro'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const reset = () => {
    setEmail(''); setPassword(''); setNombre(''); setError(null);
  };

  const handleClose = () => { reset(); onClose(); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = tab === 'login'
        ? await api.loginConEmail(email.trim(), password)
        : await api.registrarConEmail(email.trim(), password, nombre.trim());

      localStorage.setItem(TOKEN_KEY, data.access_token);
      api.setToken(data.access_token);
      onLoggedIn({
        id: String(data.usuario.id),
        nombre: data.usuario.discord_username,
        email: '',
        avatarUrl: data.usuario.discord_avatar_url || '',
        discordId: data.usuario.discord_id,
        rol: data.usuario.es_organizador ? 'organizador' : 'jugador',
      });
      reset();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo completar la acción. Intentá de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-fondo border border-borde rounded-[6px] shadow-2xl p-6 sm:p-8 space-y-6 overflow-hidden">
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-acento/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-elevada rounded-full blur-3xl pointer-events-none" />

        <button
          onClick={handleClose}
          className="absolute top-5 right-5 text-tinta-3 hover:text-white transition-colors p-1.5 rounded-[4px] hover:bg-elevada"
        >
          <X size={18} />
        </button>

        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-elevada/80 border border-acento/30 text-acento-claro text-xs font-semibold mb-2">
            <Sparkles size={12} />
            <span>Acceso al Sistema</span>
          </div>
          <h2 className="text-xl font-bold text-white">{tab === 'login' ? 'Iniciar Sesión' : 'Crear Cuenta'}</h2>
        </div>

        <div className="flex rounded-[6px] bg-superficie/90 p-1 border border-borde text-xs font-semibold">
          <button
            onClick={() => { setTab('login'); setError(null); }}
            className={`flex-1 py-2 rounded-[4px] transition-all ${tab === 'login' ? 'bg-acento text-white shadow-md' : 'text-tinta-3 hover:text-white'}`}
          >
            Iniciar Sesión
          </button>
          <button
            onClick={() => { setTab('registro'); setError(null); }}
            className={`flex-1 py-2 rounded-[4px] transition-all ${tab === 'registro' ? 'bg-acento text-white shadow-md' : 'text-tinta-3 hover:text-white'}`}
          >
            Registrarme
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-[6px] bg-rose-950/60 border border-rose-500/40 text-vivo text-xs flex items-center gap-2">
              <AlertCircle size={15} /> <span>{error}</span>
            </div>
          )}

          {tab === 'registro' && (
            <div>
              <label className="block text-xs font-semibold text-tinta-2 mb-1">Nombre</label>
              <div className="relative">
                <User className="absolute left-3 top-3 w-4 h-4 text-tinta-4" />
                <input
                  type="text" required value={nombre} onChange={e => setNombre(e.target.value)}
                  placeholder="Tu nombre"
                  className="w-full pl-9 pr-3 py-2.5 glass-card text-white text-xs focus:outline-none focus:border-acento"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-tinta-2 mb-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 w-4 h-4 text-tinta-4" />
              <input
                type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="tu@email.com"
                className="w-full pl-9 pr-3 py-2.5 glass-card text-white text-xs focus:outline-none focus:border-acento"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-tinta-2 mb-1">Contraseña</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 w-4 h-4 text-tinta-4" />
              <input
                type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)}
                placeholder="Mínimo 8 caracteres"
                className="w-full pl-9 pr-3 py-2.5 glass-card text-white text-xs focus:outline-none focus:border-acento"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-[6px] bg-acento text-white font-bold text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-60"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : (tab === 'login' ? 'Iniciar Sesión' : 'Crear Cuenta')}
          </button>
        </form>

        <p className="text-[11px] text-tinta-4 text-center leading-relaxed">
          El login con Discord va a estar disponible más adelante.
        </p>
      </div>
    </div>
  );
}
