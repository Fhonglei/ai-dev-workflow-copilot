import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Dev Workflow Copilot',
  description: 'AI-powered GitHub issue, PR, and webhook triage workflow dashboard.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

