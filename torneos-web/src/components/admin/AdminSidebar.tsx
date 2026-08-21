'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, Trophy, Users, ShieldAlert, ClipboardList,
  ChevronDown, ChevronRight, Plus, Menu, X, Settings,
  Swords, ListChecks, Crown, LogOut, ArrowLeft, ExternalLink
} from 'lucide-react';
import { api } from '@/lib/api';
import { ApiEdicion, ApiTorneo } from '@/lib/api-types';
import { Usuario } from '@/types';

const TOKEN_KEY = 'torneos_auth_token';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

export default function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedTorneo, setExpandedTorneo] = useState<number | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [torneos, setTorneos] = useState<ApiTorneo[]>([]);
  const [edicionesPorTorneo, setEdicionesPorTorneo] = useState<Record<number, ApiEdicion[]>>({});
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  useEffect(() => {
    api.getTorneos().then(t => setTorneos(t.map(x => ({ id: Number(x.id), nombre: x.nombre, slug: x.slug, descripcion: null, logo_url: null })))).catch(() => {});
    api.getMe().then(setUsuario).catch(() => {});
  }, [pathname]);

  const toggleTorneo = async (torneoId: number) => {
    if (expandedTorneo === torneoId) {
      setExpandedTorneo(null);
      return;
    }
    setExpandedTorneo(torneoId);
    if (!edicionesPorTorneo[torneoId]) {
      try {
        const ediciones = await api.getEdicionesByTorneo(String(torneoId));
        setEdicionesPorTorneo(prev => ({ ...prev, [torneoId]: ediciones }));
      } catch {}
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    api.setToken(null);
    router.push('/');
  };

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

  const nav: NavItem[] = [
    { href: '/admin', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
    { href: '/admin/inscripciones', label: 'Inscripciones', icon: <ClipboardList size={18} /> },
  ];

  const edicionLinks = (torneoId: number, edId: number) => [
    { href: `/admin/torneos/${torneoId}/ediciones/${edId}/participantes`, label: 'Participantes', icon: <Users size={15} /> },
    { href: `/admin/torneos/${torneoId}/ediciones/${edId}/fases`, label: 'Fases', icon: <Swords size={15} /> },
    { href: `/admin/torneos/${torneoId}/ediciones/${edId}/disputas`, label: 'Disputas', icon: <ShieldAlert size={15} /> },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10">
        <Link href="/admin" className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
            <Crown size={16} className="text-white" />
          </div>
          {!collapsed && (
            <span className="font-bold text-white text-sm leading-tight">
              Torneo<br /><span className="text-violet-400 text-xs font-normal">Admin Panel</span>
            </span>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto text-white/40 hover:text-white transition-colors hidden lg:block"
        >
          <Menu size={16} />
        </button>
      </div>

      <div className="px-2 pt-3 pb-1">
        <Link
          href="/"
          className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all group ${collapsed ? 'justify-center px-2' : ''}`}
          title="Volver a la página principal"
        >
          <ArrowLeft size={14} className="text-purple-400 group-hover:-translate-x-1 transition-transform flex-shrink-0" />
          {!collapsed && (
            <div className="flex items-center justify-between w-full">
              <span>Volver a la Web</span>
              <ExternalLink size={12} className="text-slate-500 group-hover:text-slate-300 transition-colors" />
            </div>
          )}
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all relative group ${
              isActive(item.href) && pathname === item.href ? 'bg-violet-600 text-white' : 'text-white/60 hover:text-white hover:bg-white/10'
            }`}
          >
            <span className="flex-shrink-0">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </Link>
        ))}

        <div className="mt-4">
          <div className="flex items-center justify-between px-3 mb-2">
            {!collapsed && (
              <span className="text-xs font-semibold text-white/30 uppercase tracking-wider">Mis Torneos</span>
            )}
            <Link
              href="/admin/torneos/nuevo"
              className="p-1 text-violet-400 hover:text-violet-300 hover:bg-violet-500/20 rounded transition-all"
              title="Crear torneo"
            >
              <Plus size={14} />
            </Link>
          </div>

          <Link
            href="/admin/torneos"
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all mb-1 ${
              pathname === '/admin/torneos' ? 'bg-violet-600 text-white' : 'text-white/60 hover:text-white hover:bg-white/10'
            }`}
          >
            <Trophy size={18} className="flex-shrink-0" />
            {!collapsed && <span>Ver todos</span>}
          </Link>

          {!collapsed && torneos.map((torneo) => {
            const isExpanded = expandedTorneo === torneo.id;
            const torneoActive = pathname.includes(`/admin/torneos/${torneo.id}`);
            const ediciones = edicionesPorTorneo[torneo.id] || [];

            return (
              <div key={torneo.id} className="mb-1">
                <button
                  onClick={() => toggleTorneo(torneo.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                    torneoActive ? 'text-white bg-white/10' : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                  }`}
                >
                  <span className="truncate flex-1 text-left">{torneo.nombre}</span>
                  {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                </button>

                {isExpanded && (
                  <div className="ml-4 mt-1 space-y-0.5">
                    <Link
                      href={`/admin/torneos/${torneo.id}`}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-all ${
                        pathname === `/admin/torneos/${torneo.id}` ? 'text-violet-300 bg-violet-500/20' : 'text-white/40 hover:text-white/70 hover:bg-white/5'
                      }`}
                    >
                      <Settings size={12} />
                      <span>Configuración</span>
                    </Link>

                    <div className="mt-1">
                      <span className="px-3 text-xs text-white/20 font-semibold uppercase tracking-wider">Ediciones</span>
                      {ediciones.length === 0 && (
                        <p className="px-3 py-1 text-[11px] text-white/25">Sin ediciones todavía</p>
                      )}
                      {ediciones.map((ed) => (
                        <div key={ed.id} className="mt-0.5 ml-2 space-y-0.5">
                          <span className="px-2 text-[11px] text-white/40 truncate block">{ed.nombre}</span>
                          {edicionLinks(torneo.id, ed.id).map((link) => (
                            <Link
                              key={link.href}
                              href={link.href}
                              className={`flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-all ${
                                isActive(link.href) ? 'text-cyan-400 bg-cyan-500/10' : 'text-white/35 hover:text-white/65 hover:bg-white/5'
                              }`}
                            >
                              {link.icon}
                              <span>{link.label}</span>
                            </Link>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-violet-950 border border-violet-500/40 flex items-center justify-center flex-shrink-0">
            <Crown size={14} className="text-violet-300" />
          </div>
          {!collapsed && usuario && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate">{usuario.nombre}</p>
              <p className="text-xs text-violet-400 capitalize">{usuario.rol}</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="text-white/40 hover:text-red-400 transition-colors p-1 rounded hover:bg-white/5"
            title="Cerrar sesión y salir"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 p-2 bg-[#0e0e1a] border border-white/10 rounded-lg text-white lg:hidden"
      >
        <Menu size={20} />
      </button>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className="relative w-72 h-full bg-[#0e0e1a] border-r border-white/10">
            <button onClick={() => setMobileOpen(false)} className="absolute top-4 right-4 text-white/50 hover:text-white">
              <X size={20} />
            </button>
            {sidebarContent}
          </div>
        </div>
      )}

      <aside
        className={`hidden lg:flex flex-col h-screen sticky top-0 bg-[#0e0e1a] border-r border-white/10 transition-all duration-300 flex-shrink-0 ${collapsed ? 'w-16' : 'w-64'}`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
