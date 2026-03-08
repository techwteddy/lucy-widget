'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, MessageCircle } from 'lucide-react'

export default function ConversationsPage() {
  const params = useParams()
  const chatbotId = params.id as string

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

      <div className="rounded-lg border border-dashed border-border p-12 text-center">
        <MessageCircle className="mx-auto h-8 w-8 text-muted-foreground mb-3" />
        <p className="text-muted-foreground">
          Conversation history will appear here once customers start chatting.
        </p>
      </div>
    </div>
  )
}
