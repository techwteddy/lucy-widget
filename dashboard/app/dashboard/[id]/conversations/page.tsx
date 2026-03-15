'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, MessageCircle, ChevronDown, ChevronRight, User, Bot } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import type { Conversation, ConversationMessage } from '@/lib/types'

export default function ConversationsPage() {
  const params = useParams()
  const router = useRouter()
  const chatbotId = params.id as string

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Record<string, ConversationMessage[]>>({})
  const [loadingMessages, setLoadingMessages] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/login')
      return
    }

    apiFetch<Conversation[]>(`/api/v1/chatbots/${chatbotId}/conversations`)
      .then(setConversations)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load conversations'))
      .finally(() => setLoading(false))
  }, [chatbotId, router])

  async function toggleConversation(convId: string) {
    if (expandedId === convId) {
      setExpandedId(null)
      return
    }

    setExpandedId(convId)

    if (messages[convId]) return

    setLoadingMessages(convId)
    try {
      const msgs = await apiFetch<ConversationMessage[]>(
        `/api/v1/chatbots/${chatbotId}/conversations/${convId}/messages`
      )
      setMessages((prev) => ({ ...prev, [convId]: msgs }))
    } catch {
      setMessages((prev) => ({ ...prev, [convId]: [] }))
    } finally {
      setLoadingMessages(null)
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <p className="text-muted-foreground">Loading conversations...</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6">
        <Link
          href={`/dashboard/${chatbotId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to chatbot
        </Link>
        <h1 className="text-2xl font-bold text-foreground">Conversations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          View chat history and customer interactions.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {conversations.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <MessageCircle className="mx-auto h-8 w-8 text-muted-foreground mb-3" />
          <p className="text-muted-foreground">
            Conversation history will appear here once customers start chatting.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {conversations.map((conv) => (
            <div key={conv.id} className="rounded-lg border border-border bg-card overflow-hidden">
              <button
                onClick={() => toggleConversation(conv.id)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {expandedId === conv.id ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                  <div>
                    <span className="text-sm font-medium text-foreground">
                      {conv.session_id}
                    </span>
                    <p className="text-xs text-muted-foreground">
                      {conv.message_count} messages
                    </p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">
                  {formatDate(conv.created_at)}
                </span>
              </button>

              {expandedId === conv.id && (
                <div className="border-t border-border px-4 py-3 bg-muted/30">
                  {loadingMessages === conv.id ? (
                    <p className="text-sm text-muted-foreground py-2">Loading messages...</p>
                  ) : (messages[conv.id] || []).length === 0 ? (
                    <p className="text-sm text-muted-foreground py-2">No messages found.</p>
                  ) : (
                    <div className="space-y-3">
                      {(messages[conv.id] || []).map((msg) => (
                        <div key={msg.id} className="flex gap-2">
                          <div className="flex-shrink-0 mt-0.5">
                            {msg.role === 'user' ? (
                              <User className="h-4 w-4 text-blue-500" />
                            ) : (
                              <Bot className="h-4 w-4 text-green-500" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium text-foreground capitalize">
                                {msg.role}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {formatDate(msg.created_at)}
                              </span>
                            </div>
                            <p className="text-sm text-foreground mt-0.5 whitespace-pre-wrap break-words">
                              {msg.content}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
