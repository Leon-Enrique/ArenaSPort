import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import { api } from '@/lib/api';
import TorneoDetailClient from './TorneoDetailClient';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const resumen = await api.getEdicionBySlug(slug).catch(() => null);
  if (!resumen) {
    return { title: 'Torneo no encontrado | Arena Esports' };
  }
  const { edicion, juego } = resumen;
  const titulo = `${edicion.nombre} | Arena Esports`;
  const descripcion = `${juego.nombre} · ${edicion.bolsa_premios ? `Bolsa de premios: ${edicion.bolsa_premios} · ` : ''}${resumen.equipos_aprobados} equipos inscritos.`;
  return {
    title: titulo,
    description: descripcion,
    openGraph: {
      title: titulo,
      description: descripcion,
      type: 'website',
    },
  };
}

export default async function TorneoDetailPage({ params }: PageProps) {
  const { slug } = await params;
  const resumen = await api.getEdicionBySlug(slug).catch(() => null);

  if (!resumen) {
    notFound();
  }

  return (
    <div className="min-h-screen flex flex-col bg-fondo text-tinta selection:bg-acento selection:text-white">
      <Navbar />
      <main className="flex-1">
        <TorneoDetailClient resumenInicial={resumen} />
      </main>
      <Footer />
    </div>
  );
}
