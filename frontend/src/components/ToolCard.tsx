import Link from 'next/link'
import { ToolItem } from '@/lib/api'

const pricingStyles: Record<string, string> = {
  free: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  freemium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  paid: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
}

const pricingLabels: Record<string, string> = {
  free: 'Kostenlos',
  freemium: 'Freemium',
  paid: 'Kostenpflichtig',
}

export default function ToolCard({ tool }: { tool: ToolItem }) {
  const href = tool.slug ? `/tools/${tool.slug}` : `/tools/${tool.id}`

  return (
    <Link
      href={href}
      className="group block rounded-xl border border-gray-800 bg-gray-900/50 p-5 card-hover"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-gray-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
          {tool.name}
        </h3>
        {tool.pricing && (
          <span className={`shrink-0 rounded-md border px-2 py-0.5 text-[10px] font-semibold ${pricingStyles[tool.pricing] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}>
            {pricingLabels[tool.pricing] || tool.pricing}
          </span>
        )}
      </div>
      {tool.description && (
        <p className="mt-2 text-xs leading-relaxed text-gray-400 line-clamp-2">
          {tool.description}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {tool.category && (
          <span className="rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-medium text-indigo-300">
            {tool.category}
          </span>
        )}
        {tool.source && (
          <span className="rounded-full bg-gray-800 px-2 py-0.5 text-[10px] text-gray-500">
            {tool.source}
          </span>
        )}
      </div>
    </Link>
  )
}
