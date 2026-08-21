import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Arena Esports | Plataforma de Torneos MLBB, Free Fire & CODM",
  description: "Plataforma de torneos de esports móviles para LATAM. Inscribe a tu equipo, sigue los brackets en vivo y consulta las tablas acumulativas.",
  keywords: ["esports", "torneos mlbb", "torneo free fire", "codm", "mobile legends", "brackets", "latam"],
  openGraph: {
    title: "Arena Esports | Plataforma de Torneos LATAM",
    description: "Sigue los brackets en vivo, tabla acumulativa de posiciones y reportes de partidas.",
    url: "https://torneos.arenaesports.com",
    siteName: "Arena Esports",
    locale: "es_LA",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${inter.variable} ${jetbrainsMono.variable} dark antialiased`}>
      <body className="min-h-screen bg-[#0a0e17] text-slate-100 font-sans">
        {children}
      </body>
    </html>
  );
}
