'use client'

import Link from 'next/link'
import { NewsItem } from '@/lib/api'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffH = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffH < 1) return 'Gerade eben'
  if (diffH < 24) return `vor ${diffH}h`
  if (diffH < 48) return 'Gestern'
  return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const sourceColors: Record<string, string> = {
  techcrunch: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  venturebeat: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  therundown: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  openai: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  'ai-news': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  'the-verge': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  'ars-technica': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  wired: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
  'google-ai': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  huggingface: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  'mit-tech-review': 'bg-red-500/10 text-red-400 border-red-500/20',
}

export default function NewsCard({ news }: { news: NewsItem }) {
  const title = news.title_de || news.title
  const summary = news.summary_de || news.summary || ''
  const colorClass = sourceColors[news.source || ''] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'

  return (
    <div className="group relative">
      <Link
        href={`/news/${news.id}`}
        className="block rounded-xl border border-gray-800 bg-gray-900/50 p-5 card-hover"
      >
        <div className="flex items-start justify-between gap-3">
          <span className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${colorClass}`}>
            {news.source || 'Unbekannt'}
          </span>
          <span className="shrink-0 text-xs text-gray-500">
            {formatDate(news.published_at || news.fetched_at)}
          </span>
        </div>
        <h3 className="mt-3 text-sm font-semibold leading-snug text-gray-100 group-hover:text-indigo-300 transition-colors line-clamp-2">
          {title}
        </h3>
        {summary && (
          <p className="mt-2 text-xs leading-relaxed text-gray-400 line-clamp-2 group-hover:line-clamp-5 transition-all">
            {summary}
          </p>
        )}
        {news.category && (
          <div className="mt-3 flex items-center gap-2">
            <span className="rounded-full bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400">
              {news.category}
            </span>
          </div>
        )}
      </Link>
    </div>
  )
}
