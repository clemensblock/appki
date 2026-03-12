import type { Metadata } from 'next'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import NewsCard from '@/components/NewsCard'
import { fetchNews } from '@/lib/api'

export const metadata: Metadata = {
  title: 'KI-News',
  description: 'Aktuelle Nachrichten aus der Welt der Künstlichen Intelligenz — täglich aktualisiert aus den wichtigsten internationalen Quellen.',
}

export const dynamic = 'force-dynamic'
export const revalidate = 120

export default async function NewsPage() {
  const news = await fetchNews({ limit: 50 })

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-10">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            KI-News
          </h1>
          <p className="mt-3 text-gray-400">
            Aktuelle Nachrichten aus der Welt der Künstlichen Intelligenz — automatisch übersetzt und zusammengefasst.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {news.map((item) => (
            <NewsCard key={item.id} news={item} />
          ))}
        </div>
        {news.length === 0 && (
          <p className="text-center text-gray-500 py-20">Keine News vorhanden.</p>
        )}
      </main>
      <Footer />
    </>
  )
}
