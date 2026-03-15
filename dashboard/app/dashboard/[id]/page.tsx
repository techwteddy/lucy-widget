'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { FileText, MessageCircle, Save, BarChart3, MessagesSquare, TrendingUp } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { EmbedSnippet } from '@/components/EmbedSnippet'
import type { Chatbot, Analytics } from '@/lib/types'

export default function ChatbotDetailPage() {
  const params = useParams()
  const router = useRouter()
  const chatbotId = params.id as string

  const [chatbot, setChatbot] = useState<Chatbot | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [analytics, setAnalytics] = useState<Analytics | null>(null)

  // Editable fields
  const [name, setName] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')
  const [welcomeMessage, setWelcomeMessage] = useState('')
  const [primaryColor, setPrimaryColor] = useState('')
  const [title, setTitle] = useState('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }

    apiFetch<Chatbot[]>('/api/v1/chatbots')
      .then((chatbots) => {
        const found = chatbots.find((c) => c.id === chatbotId)
        if (!found) {
          setError('Chatbot not found')
          return
        }
        setChatbot(found)
        setName(found.name)
        setSystemPrompt(found.system_prompt)
        setWelcomeMessage(found.welcome_message)
        setPrimaryColor(found.primary_color)
        setTitle(found.title)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load chatbot'))
      .finally(() => setLoading(false))

    apiFetch<Analytics>(`/api/v1/chatbots/${chatbotId}/analytics`)
      .then(setAnalytics)
      .catch(() => {})
  }, [chatbotId, router])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)

    try {
      const updated = await apiFetch<Chatbot>(`/api/v1/chatbots/${chatbotId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name,
          system_prompt: systemPrompt,
          welcome_message: welcomeMessage,
          primary_color: primaryColor,
          title,
        }),
      })
      setChatbot(updated)
      setSuccess('Settings saved')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  if (!chatbot) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <p className="text-red-700">{error || 'Chatbot not found'}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">{chatbot.name}</h1>
        <div className="flex items-center gap-3">
          <Link
            href={`/dashboard/${chatbotId}/knowledge`}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            <FileText className="h-4 w-4" />
            Knowledge Base
          </Link>
          <Link
            href={`/dashboard/${chatbotId}/conversations`}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            <MessageCircle className="h-4 w-4" />
            Conversations
          </Link>
        </div>
      </div>

      {/* Analytics cards */}
      {analytics && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <MessageCircle className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Conversations</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{analytics.total_conversations}</p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <MessagesSquare className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Messages</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{analytics.total_messages}</p>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs font-medium uppercase tracking-wide">Avg / Conv</span>
            </div>
            <p className="text-2xl font-bold text-foreground">{analytics.avg_messages_per_conversation}</p>
          </div>
        </div>
      )}

      {/* Embed snippet */}
      <div className="mb-8">
        <EmbedSnippet
          chatbotId={chatbotId}
          primaryColor={primaryColor}
          title={title}
        />
      </div>

      {/* Settings form */}
      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      {success && (
        <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-700">{success}</div>
      )}

      <form onSubmit={handleSave} className="space-y-5 rounded-lg border border-border bg-card p-6">
        <h2 className="font-semibold text-foreground">Settings</h2>

        <div>
          <label htmlFor="name" className="block text-sm font-medium text-foreground mb-1">Name</label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div>
          <label htmlFor="system_prompt" className="block text-sm font-medium text-foreground mb-1">System Prompt</label>
          <textarea
            id="system_prompt"
            rows={4}
            required
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y"
          />
        </div>

        <div>
          <label htmlFor="welcome_message" className="block text-sm font-medium text-foreground mb-1">Welcome Message</label>
          <input
            id="welcome_message"
            type="text"
            value={welcomeMessage}
            onChange={(e) => setWelcomeMessage(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="primary_color" className="block text-sm font-medium text-foreground mb-1">Primary Color</label>
            <div className="flex items-center gap-2">
              <input
                id="primary_color"
                type="color"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="h-9 w-12 cursor-pointer rounded border border-input"
              />
              <span className="text-sm text-muted-foreground">{primaryColor}</span>
            </div>
          </div>
          <div>
            <label htmlFor="title" className="block text-sm font-medium text-foreground mb-1">Widget Title</label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          <Save className="h-4 w-4" />
          {saving ? 'Saving...' : 'Save changes'}
        </button>
      </form>
    </div>
  )
}
