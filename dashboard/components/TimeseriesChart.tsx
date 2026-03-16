'use client'

import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { apiFetch } from '@/lib/api'

interface TimeseriesPoint {
  date: string
  message_count: number
}

interface TimeseriesData {
  chatbot_id: string
  days: number
  data: TimeseriesPoint[]
}

interface TimeseriesChartProps {
  chatbotId: string
}

export function TimeseriesChart({ chatbotId }: TimeseriesChartProps) {
  const [data, setData] = useState<TimeseriesPoint[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch<TimeseriesData>(`/api/v1/chatbots/${chatbotId}/analytics/timeseries?days=30`)
      .then((res) => setData(res.data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load chart'))
      .finally(() => setLoading(false))
  }, [chatbotId])

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="h-[250px] animate-pulse rounded bg-muted" />
      </div>
    )
  }

  if (error || !data) {
    return null
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wide">
        Messages (Last 30 days)
      </h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(val: string) => val.slice(5)}
          />
          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          <Tooltip
            labelFormatter={(label: string) => `Date: ${label}`}
            formatter={(value: number) => [value, 'Messages']}
          />
          <Area
            type="monotone"
            dataKey="message_count"
            stroke="#3B82F6"
            fill="#3B82F6"
            fillOpacity={0.15}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
