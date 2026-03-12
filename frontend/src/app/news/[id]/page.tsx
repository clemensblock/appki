import type { Metadata } from 'next'
import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { fetchNewsById } from '@/lib/api'

export const revalidate = 120

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  try {
    const news = await fetchNewsById(Number(params.id))
    const title = news.title_de || news.title
    return {
      title,
      description: news.summary_de || news.summary || title,
      openGraph: {
        title,
        description: news.summary_de || news.summary || title,
        type: 'article',
        locale: 'de_DE',
      },
    }
  } catch {
    return { title: 'News nicht gefunden' }
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default async function NewsDetailPage({ params }: { params: { id: string } }) {
  let news
  try {
    news = await fetchNewsById(Number(params.id))
  } catch {
    return (
      <>
        <Header />
        <main className="mx-auto max-w-3xl px-4 py-20 text-center">
          <h1 className="text-2xl font-bold">News nicht gefunden</h1>
          <Link href="/news" className="mt-4 inline-block text-indigo-400 hover:text-indigo-300">
            &larr; Zurueck zu den News
          </Link>
        </main>
        <Footer />
      </>
    )
  }

  const title = news.title_de || news.title
  const summary = news.summary_de || news.summary

  return (
    <>
      <Header />
      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <Link href="/news" className="inline-flex items-center text-sm text-indigo-400 hover:text-indigo-300 transition-colors mb-8">
          &larr; Alle News
        </Link>

        <article>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            {news.source && (
              <span className="rounded-md bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 font-semibold uppercase tracking-wider text-indigo-400">
                {news.source}
              </span>
            )}
            {news.category && (
              <span className="rounded-full bg-gray-800 px-2 py-0.5 text-gray-400">
                {news.category}
              </span>
            )}
            <span>{formatDate(news.published_at || news.fetched_at)}</span>
          </div>

          <h1 className="mt-6 text-3xl font-extrabold tracking-tight sm:text-4xl leading-tight">
            {title}
          </h1>

          {summary && (
            <div className="mt-8 rounded-xl border border-gray-800 bg-gray-900/50 p-6">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Zusammenfassung</h2>
              <p className="text-gray-300 leading-relaxed whitespace-pre-line">
                {summary}
              </p>
            </div>
          )}

          {news.title !== title && (
            <div className="mt-6 rounded-xl border border-gray-800/50 bg-gray-900/30 p-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-600 mb-2">Originaltitel</h2>
              <p className="text-sm text-gray-500 italic">{news.title}</p>
            </div>
          )}

          <div className="mt-8 flex items-center gap-4">
            <a
              href={news.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all hover:bg-indigo-500 hover:shadow-indigo-500/40"
            >
              Originalquelle besuchen
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
          </div>
        </article>
      </main>
      <Footer />
    </>
  )
}
