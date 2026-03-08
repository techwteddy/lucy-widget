'use client'

import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

interface EmbedSnippetProps {
  chatbotId: string
  apiKey?: string
  primaryColor?: string
  title?: string
}

export function EmbedSnippet({ chatbotId, apiKey, primaryColor, title }: EmbedSnippetProps) {
  const [copied, setCopied] = useState(false)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const snippet = `<script src="${apiUrl}/widget/chatbot.min.js"
  data-chatbot-id="${chatbotId}"${apiKey ? `\n  data-api-key="${apiKey}"` : ''}${primaryColor ? `\n  data-primary-color="${primaryColor}"` : ''}${title ? `\n  data-title="${title}"` : ''}></script>`

  async function handleCopy() {
    await navigator.clipboard.writeText(snippet)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-foreground">Embed Code</h3>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90 transition-opacity"
          aria-label="Copy embed code"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs text-muted-foreground">
        <code>{snippet}</code>
      </pre>
    </div>
  )
}
