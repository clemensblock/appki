import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'app.ki — KI-Apps & News fuer den deutschsprachigen Raum',
    template: '%s | app.ki',
  },
  description: 'Die fuehrende Informationsplattform fuer KI-Apps im deutschsprachigen Raum. Taeglich aktualisierte News, App-Bewertungen und Vergleiche.',
  openGraph: {
    type: 'website',
    locale: 'de_DE',
    siteName: 'app.ki',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="de">
      <body>
        <div className="min-h-screen flex flex-col">
          {children}
        </div>
      </body>
    </html>
  )
}
