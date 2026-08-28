import React from 'react';
import Link from 'next/link';
import { Trophy, Shield, Gamepad2, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-borde bg-fondo text-tinta-3 text-xs py-10 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-4 gap-8">
        
        {/* Brand info */}
        <div className="space-y-3 md:col-span-1">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-acento-claro" />
            <span className="font-extrabold text-sm text-white tracking-wider">
              ARENA<span className="text-acento-claro">ESPORTS</span>
            </span>
          </div>
          <p className="text-tinta-3 leading-relaxed text-[11px]">
            Plataforma integral de gestión de torneos de esports móviles para LATAM. Soporte nativo para Mobile Legends, Free Fire y CODM.
          </p>
        </div>

        {/* Competencias */}
        <div className="space-y-2">
          <h4 className="text-white font-semibold text-xs tracking-wider uppercase flex items-center gap-1.5">
            <Gamepad2 className="w-3.5 h-3.5 text-tinta-2" /> Torneos
          </h4>
          <ul className="space-y-1.5 text-[11px]">
            <li><Link href="/" className="hover:text-acento-claro transition-colors">Ver todos los torneos</Link></li>
          </ul>
        </div>

        {/* Recursos */}
        <div className="space-y-2">
          <h4 className="text-white font-semibold text-xs tracking-wider uppercase flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5 text-acento-claro" /> Competidores
          </h4>
          <ul className="space-y-1.5 text-[11px]">
            <li><Link href="/perfil" className="hover:text-white transition-colors">Mi Perfil</Link></li>
          </ul>
        </div>

        {/* Social */}
        <div className="space-y-3">
          <h4 className="text-white font-semibold text-xs tracking-wider uppercase">Comunidad</h4>
          <p className="text-[11px] text-tinta-3">Únete a nuestra comunidad de Discord para organizar y coordinar tus partidas.</p>
        </div>

      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 pt-6 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between text-[11px] text-tinta-3">
        <p>© 2026 Arena Esports Platform. Todos los derechos reservados.</p>
        <p className="flex items-center gap-1 mt-2 sm:mt-0">
          Diseñado con <Heart className="w-3 h-3 text-rose-500 fill-rose-500" /> para competidores de LATAM
        </p>
      </div>
    </footer>
  );
}
