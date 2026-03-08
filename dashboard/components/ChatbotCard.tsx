import Link from 'next/link'
import { MessageSquare } from 'lucide-react'
import type { Chatbot } from '@/lib/types'

interface ChatbotCardProps {
  chatbot: Chatbot
}

export function ChatbotCard({ chatbot }: ChatbotCardProps) {
  return (
    <Link
      href={`/dashboard/${chatbot.id}`}
      className="block rounded-lg border border-border bg-card p-5 hover:border-primary/50 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-lg"
            style={{ backgroundColor: chatbot.primary_color + '20' }}
          >
            <MessageSquare className="h-5 w-5" style={{ color: chatbot.primary_color }} />
          </div>
          <div>
            <h3 className="font-medium text-foreground">{chatbot.name}</h3>
            <p className="text-sm text-muted-foreground">{chatbot.title}</p>
          </div>
        </div>
        <span
          data-testid="status-badge"
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            chatbot.is_active
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {chatbot.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>
    </Link>
  )
}
