import type { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  return ['/', '/companion'].map(path => ({ url: `https://path-forge-v2.vercel.app${path}` }))
}
