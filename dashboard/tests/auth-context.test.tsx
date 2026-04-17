import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '@/lib/auth-context'

const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}))

function TestConsumer() {
  const { token, isLoading, logout } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="token">{token ?? 'null'}</span>
      <button onClick={logout}>Logout</button>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('reads token from localStorage on mount', async () => {
    localStorage.setItem('token', 'test-jwt-123')

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('token').textContent).toBe('test-jwt-123')
    expect(screen.getByTestId('loading').textContent).toBe('false')
  })

  it('returns null token when localStorage is empty', async () => {
    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('token').textContent).toBe('null')
    expect(screen.getByTestId('loading').textContent).toBe('false')
  })

  it('clears token and redirects on logout', async () => {
    localStorage.setItem('token', 'test-jwt-123')

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    await act(async () => {
      screen.getByText('Logout').click()
    })

    expect(localStorage.getItem('token')).toBeNull()
    expect(mockPush).toHaveBeenCalledWith('/login')
    expect(screen.getByTestId('token').textContent).toBe('null')
  })

  it('throws when useAuth is used outside AuthProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => render(<TestConsumer />)).toThrow(
      'useAuth must be used within AuthProvider'
    )

    spy.mockRestore()
  })
})
