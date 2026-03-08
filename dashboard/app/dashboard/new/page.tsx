'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { apiFetch } from '@/lib/api'
import type { CreateChatbotResponse } from '@/lib/types'

export default function NewChatbotPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [name, setName] = useState('')
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful assistant for our website visitors.')
  const [welcomeMessage, setWelcomeMessage] = useState('Hi! How can I help you today?')
  const [primaryColor, setPrimaryColor] = useState('#3B82F6')
  const [title, setTitle] = useState('Chat with us')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await apiFetch<CreateChatbotResponse>('/api/v1/chatbots/me', {
        method: 'POST',
        body: JSON.stringify({
          name,
          system_prompt: systemPrompt,
          welcome_message: welcomeMessage,
          primary_color: primaryColor,
          title,
        }),
      })
      router.push(`/dashboard/${data.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create chatbot')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-6">Create new chatbot</h1>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-foreground mb-1">
            Name
          </label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="My Support Bot"
          />
        </div>

        <div>
          <label htmlFor="system_prompt" className="block text-sm font-medium text-foreground mb-1">
            System Prompt
          </label>
          <textarea
            id="system_prompt"
            rows={4}
            required
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y"
            placeholder="You are a helpful assistant..."
          />
        </div>

        <div>
          <label htmlFor="welcome_message" className="block text-sm font-medium text-foreground mb-1">
            Welcome Message
          </label>
          <input
            id="welcome_message"
            type="text"
            value={welcomeMessage}
            onChange={(e) => setWelcomeMessage(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="primary_color" className="block text-sm font-medium text-foreground mb-1">
              Primary Color
            </label>
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
            <label htmlFor="title" className="block text-sm font-medium text-foreground mb-1">
              Widget Title
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create chatbot'}
        </button>
      </form>
    </div>
  )
}
