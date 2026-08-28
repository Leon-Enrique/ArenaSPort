import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { Trophy } from 'lucide-react';

export default function TorneoNoEncontrado() {
  return (
    <div className="min-h-screen flex flex-col bg-fondo text-tinta">
      <Navbar />
      <main className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4 py-24">
        <Trophy className="w-10 h-10 text-tinta-4" />
        <h1 className="text-xl font-bold text-white">Este torneo no existe</h1>
        <p className="text-sm text-tinta-3 max-w-sm">
          El link puede estar mal escrito o el torneo ya no está disponible.
        </p>
        <Link href="/" className="mt-2 px-5 py-2.5 rounded-[6px] accion-principal text-white text-xs font-bold transition-all">
          Volver al inicio
        </Link>
      </main>
      <Footer />
    </div>
  );
}
