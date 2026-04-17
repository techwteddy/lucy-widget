'use client'

import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import type { BillingStatus } from '@/lib/types'

const PLANS = [
  {
    name: 'Free',
    key: 'free',
    price: '$0',
    period: '',
    messages: '100 messages/mo',
    chatbots: '1 chatbot',
  },
  {
    name: 'Pro',
    key: 'pro',
    price: '$49',
    period: '/mo',
    messages: '5,000 messages/mo',
    chatbots: '5 chatbots',
  },
  {
    name: 'Business',
    key: 'business',
    price: '$149',
    period: '/mo',
    messages: '50,000 messages/mo',
    chatbots: 'Unlimited chatbots',
  },
]

export default function BillingPage() {
  const [status, setStatus] = useState<BillingStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [upgrading, setUpgrading] = useState('')

  useEffect(() => {
    apiFetch<BillingStatus>('/billing/status')
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load billing'))
      .finally(() => setLoading(false))
  }, [])

  async function handleUpgrade(plan: string) {
    setUpgrading(plan)
    setError('')
    try {
      const data = await apiFetch<{ checkout_url: string }>('/billing/checkout', {
        method: 'POST',
        body: JSON.stringify({
          plan,
          success_url: `${window.location.origin}/dashboard/billing?success=1`,
          cancel_url: `${window.location.origin}/dashboard/billing`,
        }),
      })
      window.location.href = data.checkout_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start checkout')
      setUpgrading('')
    }
  }

  async function handleManageSubscription() {
    setError('')
    try {
      const data = await apiFetch<{ portal_url: string }>('/billing/portal', {
        method: 'POST',
        body: JSON.stringify({
          return_url: `${window.location.origin}/dashboard/billing`,
        }),
      })
      window.location.href = data.portal_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open billing portal')
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <p className="text-muted-foreground">Loading billing...</p>
      </div>
    )
  }

  const usagePercent = status && status.messages_limit > 0
    ? Math.min(100, Math.round((status.messages_used / status.messages_limit) * 100))
    : 0

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-foreground mb-6">Billing</h1>

      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Current plan + usage */}
      {status && (
        <div className="mb-8 rounded-lg border border-border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-muted-foreground">Current plan</p>
              <p className="text-xl font-semibold text-foreground capitalize">{status.plan}</p>
            </div>
            {status.plan !== 'free' && (
              <button
                onClick={handleManageSubscription}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted transition-colors"
              >
                Manage Subscription
              </button>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-muted-foreground">Messages this month</span>
              <span className="text-foreground font-medium">
                {status.messages_used.toLocaleString()} / {status.messages_limit === -1 ? 'Unlimited' : status.messages_limit.toLocaleString()}
              </span>
            </div>
            {status.messages_limit > 0 && (
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    usagePercent >= 90 ? 'bg-red-500' : usagePercent >= 70 ? 'bg-yellow-500' : 'bg-primary'
                  }`}
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Plan comparison */}
      <h2 className="text-lg font-semibold text-foreground mb-4">Plans</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = status?.plan === plan.key
          return (
            <div
              key={plan.key}
              className={`rounded-lg border p-6 ${
                isCurrent ? 'border-primary bg-primary/5' : 'border-border bg-card'
              }`}
            >
              <h3 className="text-lg font-semibold text-foreground">{plan.name}</h3>
              <p className="mt-1">
                <span className="text-3xl font-bold text-foreground">{plan.price}</span>
                <span className="text-sm text-muted-foreground">{plan.period}</span>
              </p>
              <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
                <li>{plan.messages}</li>
                <li>{plan.chatbots}</li>
              </ul>
              <div className="mt-6">
                {isCurrent ? (
                  <span className="inline-block rounded-md bg-muted px-4 py-2 text-sm font-medium text-muted-foreground">
                    Current plan
                  </span>
                ) : plan.key === 'free' ? null : (
                  <button
                    onClick={() => handleUpgrade(plan.key)}
                    disabled={upgrading === plan.key}
                    className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {upgrading === plan.key ? 'Redirecting...' : `Upgrade to ${plan.name}`}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
