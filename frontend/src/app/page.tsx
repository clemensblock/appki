import Link from 'next/link'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import NewsCard from '@/components/NewsCard'
import ToolCard from '@/components/ToolCard'
import { fetchNews, fetchTools, fetchStats } from '@/lib/api'

export const dynamic = 'force-dynamic'
export const revalidate = 120

export default async function HomePage() {
  const [news, tools, stats] = await Promise.all([
    fetchNews({ limit: 6 }),
    fetchTools({ limit: 6, status: 'done' }),
    fetchStats(),
  ])

  return (
    <>
      <Header />
      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-950/40 via-gray-950 to-purple-950/30" />
          <div className="absolute inset-0">
            <div className="absolute left-1/4 top-1/4 h-96 w-96 rounded-full bg-indigo-600/10 blur-3xl" />
            <div className="absolute right-1/4 bottom-1/4 h-96 w-96 rounded-full bg-purple-600/10 blur-3xl" />
          </div>
          <div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8">
            <div className="text-center">
              <div className="inline-flex items-center rounded-full border border-indigo-500/20 bg-indigo-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-300">
                Automatisch aktualisiert
              </div>
              <h1 className="mt-6 text-4xl font-extrabold tracking-tight sm:text-6xl">
                Die führende Plattform für{' '}
                <span className="text-gradient">KI-Apps & News</span>
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-400">
                                Entdecke die besten KI-Tools, aktuelle News und Trends — täglich automatisch
                                aktualisiert aus den wichtigsten internationalen Quellen. Alles auf Deutsch.
              </p>
              <div className="mt-10 flex justify-center gap-12">
                <div className="text-center">
                  <div className="text-3xl font-extrabold text-gradient">{stats.news_gesamt.toLocaleString('de-DE')}</div>
                  <div className="mt-1 text-xs font-medium uppercase tracking-wider text-gray-500">News-Artikel</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-extrabold text-gradient">{stats.tools_gesamt.toLocaleString('de-DE')}</div>
                  <div className="mt-1 text-xs font-medium uppercase tracking-wider text-gray-500">KI-Apps</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-extrabold text-gradient">11</div>
                  <div className="mt-1 text-xs font-medium uppercase tracking-wider text-gray-500">Quellen</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Neueste News */}
        <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="mb-8 flex items-center justify-between">
            <h2 className="text-2xl font-bold">Aktuelle KI-News</h2>
            <Link href="/news" className="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
              Alle News &rarr;
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {news.map((item) => (
              <NewsCard key={item.id} news={item} />
            ))}
          </div>
        </section>

        {/* Top KI-Apps */}
        <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <div className="mb-8 flex items-center justify-between">
            <h2 className="text-2xl font-bold">Beliebte KI-Apps</h2>
            <Link href="/tools" className="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors">
              Alle Apps &rarr;
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {tools.map((tool) => (
              <ToolCard key={tool.id} tool={tool} />
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
