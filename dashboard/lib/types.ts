export interface Chatbot {
  id: string
  name: string
  system_prompt: string
  welcome_message: string
  primary_color: string
  position: string
  title: string
  owner_email: string | null
  is_active: boolean
}

export interface CreateChatbotResponse extends Chatbot {
  api_key: string
}

export interface Document {
  id: string
  filename: string
  status: string
  chunk_count: number
  error_message: string | null
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user_id: string
  email: string
}

export interface Conversation {
  id: string
  session_id: string
  message_count: number
  created_at: string
}

export interface ConversationMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface Analytics {
  chatbot_id: string
  total_conversations: number
  total_messages: number
  avg_messages_per_conversation: number
}

export interface BillingStatus {
  plan: string
  messages_used: number
  messages_limit: number
}
