import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { TimeseriesChart } from '@/components/TimeseriesChart'

// Mock recharts with minimal renderable components
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children, data }: { children: React.ReactNode; data: unknown[] }) => (
    <div data-testid="area-chart" data-points={data.length}>{children}</div>
  ),
  Area: () => <div data-testid="area" />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  CartesianGrid: () => <div />,
  Tooltip: () => <div />,
}))

const mockData = {
  chatbot_id: 'test-123',
  days: 30,
  data: Array.from({ length: 30 }, (_, i) => ({
    date: `2026-02-${String(14 + i).padStart(2, '0')}`,
    message_count: i % 5,
  })),
}

beforeEach(() => {
  vi.restoreAllMocks()
  // localStorage mock for apiFetch token
  Object.defineProperty(window, 'localStorage', {
    value: { getItem: vi.fn(() => 'test-token'), setItem: vi.fn(), removeItem: vi.fn() },
    writable: true,
  })
})

describe('TimeseriesChart', () => {
  it('shows loading skeleton while fetching', () => {
    vi.spyOn(global, 'fetch').mockImplementation(() => new Promise(() => {}))
    render(<TimeseriesChart chatbotId="test-123" />)
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('renders chart with data after successful fetch', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
      text: async () => JSON.stringify(mockData),
    } as Response)

    render(<TimeseriesChart chatbotId="test-123" />)

    await waitFor(() => {
      expect(screen.getByTestId('area-chart')).toBeInTheDocument()
    })

    expect(screen.getByTestId('area-chart').getAttribute('data-points')).toBe('30')
    expect(screen.getByText(/messages/i)).toBeInTheDocument()
  })

  it('renders nothing on error', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValueOnce({
      ok: false,
      text: async () => 'Not found',
    } as Response)

    const { container } = render(<TimeseriesChart chatbotId="test-123" />)

    await waitFor(() => {
      expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument()
    })

    expect(screen.queryByTestId('area-chart')).not.toBeInTheDocument()
  })
})
