import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  const base = process.env.NEXT_PUBLIC_SITE_URL || 'https://torneos.arenaesports.com';
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: ['/admin', '/auth/callback'] },
    ],
    sitemap: `${base}/sitemap.xml`,
  };
}
