import type { Metadata } from 'next'
import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { fetchToolBySlug } from '@/lib/api'

export const revalidate = 120

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const tool = await fetchToolBySlug(params.slug)
  if (!tool) return { title: 'Tool nicht gefunden' }
  return {
    title: `${tool.name} — KI-App`,
    description: tool.description || `${tool.name} — KI-App im Verzeichnis von app.ki`,
    openGraph: {
      title: `${tool.name} — KI-App`,
      description: tool.description || `${tool.name} — KI-App im Verzeichnis von app.ki`,
      type: 'article',
      locale: 'de_DE',
    },
  }
}

const pricingLabels: Record<string, { label: string; color: string }> = {
  free: { label: 'Kostenlos', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' },
  freemium: { label: 'Freemium', color: 'bg-amber-500/10 text-amber-400 border-amber-500/30' },
  paid: { label: 'Kostenpflichtig', color: 'bg-rose-500/10 text-rose-400 border-rose-500/30' },
}

export default async function ToolDetailPage({ params }: { params: { slug: string } }) {
  const tool = await fetchToolBySlug(params.slug)

  if (!tool) {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-3xl px-4 py-20 text-center">
          <h1 className="text-2xl font-bold">Tool nicht gefunden</h1>
          <Link href="/tools" className="mt-4 inline-block text-indigo-400 hover:text-indigo-300">
            &larr; Zurueck zum Verzeichnis
          </Link>
        </main>
        <Footer />
      </>
    )
  }

  const pricing = pricingLabels[tool.pricing || ''] || { label: tool.pricing || 'Unbekannt', color: 'bg-gray-500/10 text-gray-400 border-gray-500/30' }
  let features: string[] = []
  if (tool.features) {
    if (typeof tool.features === 'string') {
      try { features = JSON.parse(tool.features) } catch { features = [] }
    } else {
      features = tool.features
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
        <Link href="/tools" className="inline-flex items-center text-sm text-indigo-400 hover:text-indigo-300 transition-colors mb-8">
          &larr; Alle KI-Apps
        </Link>

        {/* Header */}
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{tool.name}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span className={`rounded-lg border px-3 py-1 text-xs font-semibold ${pricing.color}`}>
                {pricing.label}
              </span>
              {tool.category && (
                <span className="rounded-lg border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
                  {tool.category}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-3">
            {(tool.website_url || tool.url) && (
              <a
                href={tool.website_url || tool.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:bg-indigo-500 hover:shadow-indigo-500/40"
              >
                App besuchen
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            )}
          </div>
        </div>

        {/* Description */}
        {tool.description && (
          <div className="mt-8 rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Beschreibung</h2>
            <p className="text-gray-300 leading-relaxed">{tool.description}</p>
          </div>
        )}

        {/* Features */}
        {features.length > 0 && (
          <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4">Features</h2>
            <ul className="space-y-3">
              {features.map((feature, i) => (
                <li key={i} className="flex items-start gap-3">
                  <svg className="mt-0.5 h-5 w-5 shrink-0 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                  <span className="text-gray-300">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Target Audience */}
        {tool.target_audience && (
          <div className="mt-6 rounded-xl border border-gray-800 bg-gray-900/50 p-6">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Zielgruppe</h2>
            <p className="text-gray-300 leading-relaxed">{tool.target_audience}</p>
          </div>
        )}

        {/* Meta Info */}
        <div className="mt-6 rounded-xl border border-gray-800/50 bg-gray-900/30 p-4">
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            {tool.source && (
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-600">Quelle</span>
                <p className="mt-1 text-gray-400">{tool.source}</p>
              </div>
            )}
            {tool.enriched_at && (
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-600">Aktualisiert</span>
                <p className="mt-1 text-gray-400">{new Date(tool.enriched_at).toLocaleDateString('de-DE')}</p>
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
