import { useState } from 'react';
import Link from 'next/link';
const WaitlistModal = ({ isOpen, onClose }) => null;


// ─── Wordmark ────────────────────────────────────────────────────────────────
function SardisWordmark() {
  return (
    <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
      <svg width="34" height="34" viewBox="0 0 28 28" fill="none">
        <path
          d="M20 5H10a7 7 0 000 14h2"
          stroke="#F5F5F5"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M8 23h10a7 7 0 000-14h-2"
          stroke="#F5F5F5"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
      <span
        className="text-2xl font-bold leading-none"
        style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
      >
        Sardis
      </span>
    </Link>
  );
}

// ─── Checkmark icon ───────────────────────────────────────────────────────────
function CheckIcon({ color = '#22C55E' }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 mt-0.5">
      <path d="M3 8l3.5 3.5L13 4" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Dash icon (feature not included) ────────────────────────────────────────
function DashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 mt-0.5">
      <path d="M4 8h8" stroke="#3F3F4A" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

// ─── Pricing data ─────────────────────────────────────────────────────────────
const PLANS = [
  {
    name: 'Free',
    price: null,
    priceLabel: '$0',
    period: '/mo',
    tagline: 'Get started with no credit card.',
    highlighted: false,
    badge: null,
    cta: 'Get Started Free',
    ctaTo: '/signup',
    features: [
      { label: '1,000 API calls / mo', included: true },
      { label: '2 agents', included: true },
      { label: '1.5% transaction fee', included: true },
      { label: '$1K / mo transaction volume', included: true },
      { label: 'Shared MPC wallets', included: true },
      { label: 'Community support', included: true },
      { label: 'Basic policy engine', included: true },
      { label: 'Compliance', included: false },
    ],
  },
  {
    name: 'Starter',
    price: 49,
    priceLabel: '$49',
    period: '/mo',
    tagline: 'For small teams shipping fast.',
    highlighted: false,
    badge: null,
    cta: 'Start Free Trial',
    ctaTo: '/signup?plan=starter',
    features: [
      { label: '50,000 API calls / mo', included: true },
      { label: '10 agents', included: true },
      { label: '1.0% transaction fee', included: true },
      { label: '$25K / mo transaction volume', included: true },
      { label: 'Dedicated MPC wallets', included: true },
      { label: 'Email support', included: true },
      { label: 'Full policy engine', included: true },
      { label: 'Standard compliance', included: true },
    ],
  },
  {
    name: 'Growth',
    price: 249,
    priceLabel: '$249',
    period: '/mo',
    tagline: 'Scale your agent fleet with confidence.',
    highlighted: true,
    badge: 'Most Popular',
    cta: 'Start Free Trial',
    ctaTo: '/signup?plan=growth',
    features: [
      { label: '500,000 API calls / mo', included: true },
      { label: '100 agents', included: true },
      { label: '0.75% transaction fee', included: true },
      { label: '$250K / mo transaction volume', included: true },
      { label: 'Dedicated MPC wallets', included: true },
      { label: 'Priority support', included: true },
      { label: 'Full policy engine', included: true },
      { label: 'Full compliance', included: true },
    ],
  },
  {
    name: 'Enterprise',
    price: null,
    priceLabel: 'Custom',
    period: null,
    tagline: 'Built around your requirements.',
    highlighted: false,
    badge: null,
    cta: 'Contact Sales',
    ctaTo: '/enterprise',
    features: [
      { label: 'Unlimited API calls', included: true },
      { label: 'Unlimited agents', included: true },
      { label: '0.5% transaction fee', included: true },
      { label: 'Custom transaction volume', included: true },
      { label: 'Custom MPC wallets', included: true },
      { label: 'Dedicated support', included: true },
      { label: 'Full policy engine + custom', included: true },
      { label: 'Full compliance + audit', included: true },
    ],
  },
];

// ─── FAQ data ─────────────────────────────────────────────────────────────────
const FAQS = [
  {
    q: 'What happens when I exceed my limits?',
    a: "We send you a warning at 80% of your monthly limit. At 100% we soft-block further calls until the next billing cycle (or until you upgrade). You'll always be able to log in and manage your account.",
  },
  {
    q: 'Can I change plans anytime?',
    a: 'Yes. Upgrades take effect immediately and are prorated. Downgrades take effect at the start of the next billing cycle. You can make changes from the dashboard at any time.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major credit and debit cards via Stripe. Enterprise customers can pay via bank transfer on annual contracts.',
  },
  {
    q: 'Is there a free trial?',
    a: 'The Free tier is permanent — no credit card, no expiry. Paid tiers (Starter and Growth) come with a 14-day free trial so you can evaluate before committing.',
  },
  {
    q: 'Do you offer annual pricing?',
    a: 'Yes. Annual plans come with a meaningful discount compared to month-to-month. Contact us or reach out through the Enterprise page to discuss options.',
  },
];

// ─── FAQ Item ─────────────────────────────────────────────────────────────────
function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="rounded-xl overflow-hidden transition-colors"
      style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.07)' }}
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-4 px-6 py-5 text-left"
        aria-expanded={open}
      >
        <span
          className="text-sm font-medium"
          style={{ fontFamily: "'Inter', sans-serif", color: '#E0E0E0' }}
        >
          {q}
        </span>
        <span
          className="shrink-0 transition-transform duration-200"
          style={{ transform: open ? 'rotate(45deg)' : 'rotate(0deg)', color: '#505460' }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </span>
      </button>

      {open && (
        <div
          className="px-6 pb-5 text-sm leading-relaxed"
          style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}
        >
          {a}
        </div>
      )}
    </div>
  );
}

// ─── Plan Card ────────────────────────────────────────────────────────────────
function PlanCard({ plan, onOpenWaitlist }) {
  const borderColor = plan.highlighted
    ? '1px solid rgba(99,102,241,0.6)'
    : '1px solid rgba(255,255,255,0.08)';

  const cardBg = plan.highlighted ? '#0D0E16' : '#0A0B0D';

  return (
    <div
      className="relative flex flex-col rounded-2xl p-6"
      style={{ background: cardBg, border: borderColor }}
    >
      {/* Badge */}
      {plan.badge && (
        <div
          className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold"
          style={{
            fontFamily: "'Inter', sans-serif",
            background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
            color: '#fff',
            letterSpacing: '0.02em',
          }}
        >
          {plan.badge}
        </div>
      )}

      {/* Plan name */}
      <p
        className="text-xs font-semibold uppercase tracking-widest mb-4"
        style={{ fontFamily: "'Inter', sans-serif", color: plan.highlighted ? '#818CF8' : '#505460' }}
      >
        {plan.name}
      </p>

      {/* Price */}
      <div className="flex items-end gap-1 mb-2">
        <span
          className="text-4xl font-bold"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
        >
          {plan.priceLabel}
        </span>
        {plan.period && (
          <span
            className="text-sm mb-1"
            style={{ fontFamily: "'Inter', sans-serif", color: '#505460' }}
          >
            {plan.period}
          </span>
        )}
      </div>

      {/* Tagline */}
      <p
        className="text-sm mb-6"
        style={{ fontFamily: "'Inter', sans-serif", color: '#606070' }}
      >
        {plan.tagline}
      </p>

      {/* CTA */}
      {plan.ctaTo ? (
        <Link
          to={plan.ctaTo}
          className="block w-full text-center rounded-lg py-2.5 text-sm font-medium mb-6 transition-colors"
          style={{
            fontFamily: "'Inter', sans-serif",
            ...(plan.highlighted
              ? { background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)', color: '#fff' }
              : {
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#E0E0E0',
                }),
          }}
          onMouseEnter={(e) => {
            if (plan.highlighted) {
              e.currentTarget.style.filter = 'brightness(1.12)';
            } else {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)';
            }
          }}
          onMouseLeave={(e) => {
            if (plan.highlighted) {
              e.currentTarget.style.filter = 'brightness(1)';
            } else {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
            }
          }}
        >
          {plan.cta}
        </Link>
      ) : (
        <button
          onClick={onOpenWaitlist}
          className="block w-full text-center rounded-lg py-2.5 text-sm font-medium mb-6 transition-colors cursor-pointer"
          style={{
            fontFamily: "'Inter', sans-serif",
            ...(plan.highlighted
              ? { background: 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)', color: '#fff', border: 'none' }
              : {
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#E0E0E0',
                }),
          }}
          onMouseEnter={(e) => {
            if (plan.highlighted) {
              e.currentTarget.style.filter = 'brightness(1.12)';
            } else {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.22)';
            }
          }}
          onMouseLeave={(e) => {
            if (plan.highlighted) {
              e.currentTarget.style.filter = 'brightness(1)';
            } else {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
            }
          }}
        >
          {plan.cta}
        </button>
      )}

      {/* Divider */}
      <div className="w-full h-px mb-6" style={{ background: 'rgba(255,255,255,0.06)' }} />

      {/* Features */}
      <ul className="flex flex-col gap-3">
        {plan.features.map((f) => (
          <li key={f.label} className="flex items-start gap-3">
            {f.included ? (
              <CheckIcon color={plan.highlighted ? '#818CF8' : '#22C55E'} />
            ) : (
              <DashIcon />
            )}
            <span
              className="text-sm"
              style={{
                fontFamily: "'Inter', sans-serif",
                color: f.included ? '#A0A0AA' : '#3F3F4A',
              }}
            >
              {f.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Minimal nav used on standalone pages ─────────────────────────────────────
function MinimalNav() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b"
      style={{ backgroundColor: 'rgba(5,5,6,0.85)', borderBottomColor: 'rgba(255,255,255,0.07)' }}
    >
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
        <div className="flex items-center justify-between h-16">
          <SardisWordmark />

          <div className="hidden md:flex items-center gap-8">
            <a
              href="/docs"
              className="text-[14px] transition-colors duration-200"
              style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#C0C0C0')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#808080')}
            >
              Docs
            </a>
            <a
              href="/docs/blog"
              className="text-[14px] transition-colors duration-200"
              style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#C0C0C0')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#808080')}
            >
              Blog
            </a>
            <a
              href="/pricing"
              className="text-[14px] transition-colors duration-200"
              style={{ fontFamily: "'Inter', sans-serif", color: '#F5F5F5' }}
            >
              Pricing
            </a>
            <a
              href="/signup"
              className="text-[14px] font-medium text-white rounded-lg transition-colors duration-200 px-4 py-2"
              style={{ fontFamily: "'Inter', sans-serif", backgroundColor: '#2563EB' }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#1D4ED8')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#2563EB')}
            >
              Get Started
            </a>
          </div>
        </div>
      </div>
    </nav>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function Pricing() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#050506' }}>
      <MinimalNav />

      {/* Spacer for fixed nav */}
      <div className="h-16" />

      {/* Header */}
      <section className="pt-20 pb-4 px-5 text-center">
        <div
          className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-6 text-xs font-medium"
          style={{
            fontFamily: "'Inter', sans-serif",
            background: 'rgba(99,102,241,0.1)',
            border: '1px solid rgba(99,102,241,0.25)',
            color: '#818CF8',
          }}
        >
          Transparent pricing
        </div>

        <h1
          className="text-4xl md:text-5xl font-bold mb-4 tracking-tight"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
        >
          Simple, transparent pricing
        </h1>
        <p
          className="text-lg max-w-lg mx-auto"
          style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}
        >
          Start free, scale as you grow. No hidden fees — just the infrastructure your agents need.
        </p>
      </section>

      {/* Pricing grid */}
      <section className="max-w-[1200px] mx-auto px-5 md:px-10 pt-12 pb-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
          {PLANS.map((plan) => (
            <PlanCard key={plan.name} plan={plan} onOpenWaitlist={() => setWaitlistOpen(true)} />
          ))}
        </div>

        {/* Sub-note */}
        <p
          className="text-center text-xs mt-8"
          style={{ fontFamily: "'Inter', sans-serif", color: '#505460' }}
        >
          All paid plans include a 14-day free trial. No credit card required for the Free tier.
        </p>
      </section>

      {/* Divider */}
      <div className="max-w-[1200px] mx-auto px-5 md:px-10">
        <div className="h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
      </div>

      {/* FAQ */}
      <section className="max-w-[720px] mx-auto px-5 py-20">
        <h2
          className="text-2xl font-bold mb-10 text-center"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
        >
          Frequently asked questions
        </h2>
        <div className="flex flex-col gap-3">
          {FAQS.map((faq) => (
            <FAQItem key={faq.q} q={faq.q} a={faq.a} />
          ))}
        </div>
      </section>

      {/* Bottom CTA strip */}
      <section className="pb-24 px-5 text-center">
        <div
          className="inline-block rounded-2xl px-10 py-10 max-w-xl w-full"
          style={{ background: '#0A0B0D', border: '1px solid rgba(255,255,255,0.08)' }}
        >
          <h3
            className="text-xl font-semibold mb-3"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#F5F5F5' }}
          >
            Not sure which plan is right?
          </h3>
          <p
            className="text-sm mb-6"
            style={{ fontFamily: "'Inter', sans-serif", color: '#808080' }}
          >
            Start on the Free tier and upgrade whenever you're ready. Our team is happy to help you
            figure out the best fit.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href="/signup"
              className="rounded-lg py-3 px-6 text-sm font-medium text-white text-center transition-colors cursor-pointer inline-block"
              style={{ fontFamily: "'Inter', sans-serif", backgroundColor: '#2563EB', border: 'none' }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#1D4ED8')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#2563EB')}
            >
              Get Started Free
            </a>
            <Link
              href="/enterprise"
              className="rounded-lg py-3 px-6 text-sm font-medium text-center transition-colors"
              style={{
                fontFamily: "'Inter', sans-serif",
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#A0A0AA',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')}
            >
              Talk to sales
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        className="border-t py-8 text-center"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}
      >
        <p
          className="text-xs"
          style={{ fontFamily: "'Inter', sans-serif", color: '#3F3F4A' }}
        >
          &copy; {new Date().getFullYear()} Sardis. All rights reserved.{' '}
          <Link href="/docs/terms" className="underline" style={{ color: '#505460' }}>
            Terms
          </Link>{' '}
          &middot;{' '}
          <Link href="/docs/privacy" className="underline" style={{ color: '#505460' }}>
            Privacy
          </Link>
        </p>
      </footer>

      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </div>
  );
}
