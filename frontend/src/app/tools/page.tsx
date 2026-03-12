import type { Metadata } from 'next'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import ToolCard from '@/components/ToolCard'
import { fetchTools } from '@/lib/api'

export const metadata: Metadata = {
  title: 'KI-Apps Verzeichnis',
  description: 'Entdecke die besten KI-Apps und Tools — mit Beschreibungen, Preisen und Features. Taeglich automatisch aktualisiert.',
}

export const dynamic = 'force-dynamic'
export const revalidate = 120

export default async function ToolsPage() {
  const tools = await fetchTools({ limit: 100, status: 'done' })

  return (
    <>
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-10">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            KI-Apps Verzeichnis
          </h1>
          <p className="mt-3 text-gray-400">
            {tools.length} KI-Apps mit detaillierten Beschreibungen, Preisen und Features.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tools.map((tool) => (
            <ToolCard key={tool.id} tool={tool} />
          ))}
        </div>
        {tools.length === 0 && (
          <p className="text-center text-gray-500 py-20">Keine Tools vorhanden.</p>
        )}
      </main>
      <Footer />
    </>
  )
}
