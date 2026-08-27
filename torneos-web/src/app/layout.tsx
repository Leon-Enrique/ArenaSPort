import type { Metadata } from "next";
import { Archivo, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Archivo y no Inter: es una grotesca con más carácter, aguanta
// pantallas densas de datos, y no arrastra el aire de plantilla que
// tiene Inter por estar en todos lados.
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

// Para cifras: marcadores, IDs de juego, cupos. Los dígitos ocupan
// todos lo mismo, así que las columnas se alinean solas.
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono-jetbrains",
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
    <html lang="es" className={`${archivo.variable} ${jetbrainsMono.variable} dark antialiased`}>
      <body className="min-h-screen bg-fondo text-tinta font-sans">
        {children}
      </body>
    </html>
  );
}
