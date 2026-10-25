import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/', disallow: ['/auth/', '/companion/connect', '/analysis', '/progress', '/profile', '/recommendations'] },
    sitemap: 'https://path-forge-v2.vercel.app/sitemap.xml',
  }
}
