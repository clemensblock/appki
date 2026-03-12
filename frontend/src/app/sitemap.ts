import { MetadataRoute } from 'next'
import { fetchTools, fetchNews } from '@/lib/api'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://dev.app.ki'
  
  const staticPages: MetadataRoute.Sitemap = [
    { url: baseUrl, lastModified: new Date(), changeFrequency: 'daily', priority: 1.0 },
    { url: `${baseUrl}/news`, lastModified: new Date(), changeFrequency: 'hourly', priority: 0.9 },
    { url: `${baseUrl}/tools`, lastModified: new Date(), changeFrequency: 'daily', priority: 0.9 },
  ]

  let toolPages: MetadataRoute.Sitemap = []
  let newsPages: MetadataRoute.Sitemap = []

  try {
    const tools = await fetchTools({ limit: 100, status: 'done' })
    toolPages = tools
      .filter(t => t.slug)
      .map(t => ({
        url: `${baseUrl}/tools/${t.slug}`,
        lastModified: t.enriched_at ? new Date(t.enriched_at) : new Date(),
        changeFrequency: 'weekly' as const,
        priority: 0.7,
      }))
  } catch {}

  try {
    const news = await fetchNews({ limit: 50 })
    newsPages = news.map(n => ({
      url: `${baseUrl}/news/${n.id}`,
      lastModified: n.published_at ? new Date(n.published_at) : new Date(),
      changeFrequency: 'never' as const,
      priority: 0.5,
    }))
  } catch {}

  return [...staticPages, ...toolPages, ...newsPages]
}
