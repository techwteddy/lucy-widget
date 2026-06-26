import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import { NavActions } from '@/components/NavActions'
import { Providers } from './providers'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DinqAgent by Dinq Digital',
  description: 'Embed AI chat on any website in 60 seconds',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <header className="border-b border-border bg-card">
          <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
            <Link href="/" className="text-lg font-semibold text-foreground">
              DinqAgent by Dinq Digital
            </Link>
            <nav className="flex items-center gap-4">
              <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
              <Link href="/playground" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Playground
              </Link>
              <Link href="/dashboard/billing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Billing
              </Link>
              <NavActions />
            </nav>
          </div>
        </header>
        <Providers>
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  )
}
