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
