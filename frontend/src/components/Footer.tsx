import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-gray-800/50 bg-gray-950">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-1">
            <span className="text-xl font-extrabold text-gradient">app</span>
            <span className="text-xl font-light text-gray-400">.ki</span>
          </div>
          <nav className="flex gap-6 text-sm text-gray-500">
            <Link href="/news" className="hover:text-gray-300 transition-colors">News</Link>
            <Link href="/tools" className="hover:text-gray-300 transition-colors">KI-Apps</Link>
            <a href="/docs" className="hover:text-gray-300 transition-colors">API</a>
          </nav>
          <p className="text-xs text-gray-600">
            &copy; {new Date().getFullYear()} app.ki — Automatisch aktualisiert
          </p>
        </div>
      </div>
    </footer>
  )
}
