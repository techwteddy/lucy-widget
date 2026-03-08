import Link from 'next/link'
import { MessageSquare, Zap, Database, Users } from 'lucide-react'

const features = [
  {
    icon: Zap,
    title: 'Easy Embed',
    description: 'Add a single script tag to your site. Works everywhere — WordPress, Shopify, static HTML.',
  },
  {
    icon: Database,
    title: 'RAG-Powered',
    description: 'Upload your docs and the chatbot answers from your knowledge base using vector search.',
  },
  {
    icon: Users,
    title: 'Multi-tenant',
    description: 'Each customer gets their own chatbot with isolated data, branding, and API keys.',
  },
]

const plans = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    description: '1 chatbot, 100 messages/month',
    features: ['1 chatbot', '100 messages/month', '1 document upload', 'Community support'],
    cta: 'Get started free',
    highlighted: false,
  },
  {
    name: 'Pro',
    price: '$49',
    period: '/month',
    description: '5 chatbots, unlimited messages',
    features: ['5 chatbots', 'Unlimited messages', '50 documents', 'Custom branding', 'Priority support'],
    cta: 'Start Pro trial',
    highlighted: true,
  },
  {
    name: 'Business',
    price: '$149',
    period: '/month',
    description: 'Unlimited chatbots, white-label',
    features: ['Unlimited chatbots', 'Unlimited messages', 'Unlimited documents', 'White-label', 'API access', 'Dedicated support'],
    cta: 'Contact sales',
    highlighted: false,
  },
]

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-5xl px-4">
      {/* Hero */}
      <section className="py-20 text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary mb-6">
          <MessageSquare className="h-4 w-4" />
          AI-powered chat widget
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Embed AI chat on any website
          <br />
          <span className="text-primary">in 60 seconds</span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Upload your docs, customize the look, paste one script tag.
          Your customers get instant answers powered by RAG and Claude.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
          >
            Get started free
          </Link>
          <Link
            href="#pricing"
            className="rounded-lg border border-border px-6 py-3 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            View pricing
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="py-16">
        <h2 className="text-center text-2xl font-bold text-foreground mb-10">
          Everything you need
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {features.map((feature) => (
            <div key={feature.title} className="rounded-lg border border-border bg-card p-6">
              <feature.icon className="h-8 w-8 text-primary mb-3" />
              <h3 className="font-semibold text-foreground mb-1">{feature.title}</h3>
              <p className="text-sm text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-16" data-testid="pricing-section">
        <h2 className="text-center text-2xl font-bold text-foreground mb-10">
          Simple pricing
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-lg border p-6 ${
                plan.highlighted
                  ? 'border-primary bg-primary/5 ring-1 ring-primary'
                  : 'border-border bg-card'
              }`}
            >
              <h3 className="font-semibold text-foreground">{plan.name}</h3>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="text-3xl font-bold text-foreground">{plan.price}</span>
                <span className="text-sm text-muted-foreground">{plan.period}</span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{plan.description}</p>
              <ul className="mt-4 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-foreground">
                    <span className="text-primary">&#10003;</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/dashboard"
                className={`mt-6 block rounded-lg px-4 py-2 text-center text-sm font-medium transition-opacity hover:opacity-90 ${
                  plan.highlighted
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
