'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Plus } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { ChatbotCard } from '@/components/ChatbotCard'
import type { Chatbot } from '@/lib/types'

export default function DashboardPage() {
  const router = useRouter()
  const [chatbots, setChatbots] = useState<Chatbot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }

    apiFetch<Chatbot[]>('/api/v1/chatbots')
      .then(setChatbots)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load chatbots'))
      .finally(() => setLoading(false))
  }, [router])

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">My Chatbots</h1>
        <Link
          href="/dashboard/new"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
        >
          <Plus className="h-4 w-4" />
          New chatbot
        </Link>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {chatbots.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-muted-foreground mb-4">
            You have not created any chatbots yet.
          </p>
          <Link
            href="/dashboard/new"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
          >
            <Plus className="h-4 w-4" />
            Create your first chatbot
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {chatbots.map((chatbot) => (
            <ChatbotCard key={chatbot.id} chatbot={chatbot} />
          ))}
        </div>
      )}
    </div>
  )
}
