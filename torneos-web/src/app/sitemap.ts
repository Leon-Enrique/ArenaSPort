import type { MetadataRoute } from 'next';
import { api } from '@/lib/api';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'https://torneos.arenaesports.com';

  let ediciones: { slug: string }[] = [];
  try {
    const data = await api.getEdicionesCompletas();
    ediciones = data.filter(e => e.slug).map(e => ({ slug: e.slug as string }));
  } catch {
    ediciones = [];
  }

  return [
    { url: base, changeFrequency: 'daily', priority: 1 },
    ...ediciones.map((e): MetadataRoute.Sitemap[number] => ({
      url: `${base}/torneos/${e.slug}`,
      changeFrequency: 'hourly',
      priority: 0.8,
    })),
  ];
}
