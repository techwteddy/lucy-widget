import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmbedSnippet } from '@/components/EmbedSnippet'
import { ChatbotCard } from '@/components/ChatbotCard'
import type { Chatbot } from '@/lib/types'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({}),
}))

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

const mockChatbot: Chatbot = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  name: 'Test Bot',
  system_prompt: 'You are helpful.',
  welcome_message: 'Hello!',
  primary_color: '#3B82F6',
  position: 'bottom-right',
  title: 'Chat with us',
  owner_email: 'test@example.com',
  is_active: true,
}

describe('EmbedSnippet', () => {
  it('renders script tag in embed code', () => {
    render(<EmbedSnippet chatbotId="test-id-123" />)
    const codeBlock = screen.getByText(/chatbot\.min\.js/i)
    expect(codeBlock).toBeInTheDocument()
    expect(codeBlock.textContent).toContain('<script src=')
    expect(codeBlock.textContent).toContain('data-chatbot-id="test-id-123"')
  })

  it('has a copy button', () => {
    render(<EmbedSnippet chatbotId="test-id-123" />)
    const copyButton = screen.getByRole('button', { name: /copy/i })
    expect(copyButton).toBeInTheDocument()
  })
})

describe('ChatbotCard', () => {
  it('renders chatbot name', () => {
    render(<ChatbotCard chatbot={mockChatbot} />)
    expect(screen.getByText('Test Bot')).toBeInTheDocument()
  })

  it('renders active badge for active chatbot', () => {
    render(<ChatbotCard chatbot={mockChatbot} />)
    const badge = screen.getByTestId('status-badge')
    expect(badge).toHaveTextContent('Active')
    expect(badge.className).toContain('green')
  })

  it('renders inactive badge for inactive chatbot', () => {
    const inactive = { ...mockChatbot, is_active: false }
    render(<ChatbotCard chatbot={inactive} />)
    const badge = screen.getByTestId('status-badge')
    expect(badge).toHaveTextContent('Inactive')
    expect(badge.className).toContain('red')
  })
})

describe('Landing page pricing', () => {
  it('renders pricing section with all plans', async () => {
    const { default: LandingPage } = await import('@/app/page')
    render(<LandingPage />)

    expect(screen.getByTestId('pricing-section')).toBeInTheDocument()
    expect(screen.getByText('Free')).toBeInTheDocument()
    expect(screen.getByText('$49')).toBeInTheDocument()
    expect(screen.getByText('$149')).toBeInTheDocument()
  })
})
