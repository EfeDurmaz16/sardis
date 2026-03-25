// eslint-disable-next-line no-unused-vars -- motion is used as JSX namespace (motion.div)
import { motion } from 'framer-motion';
import Link from 'next/link';

// Font imports (fix latent bug - these packages are installed but never imported)

// Section components
// Navbar removed — landing page served from landing-next/
// Minimal inline nav for dashboard root page
function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b" style={{ backgroundColor: 'color-mix(in srgb, var(--landing-bg) 80%, transparent)', borderBottomColor: 'var(--landing-border)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
        <div className="flex items-center justify-between h-16">
          <a href="/" className="flex items-center gap-2.5">
            <svg width="34" height="34" viewBox="0 0 28 28" fill="none">
              <path d="M20 5H10a7 7 0 000 14h2" stroke="var(--landing-text-primary)" strokeWidth="3" strokeLinecap="round" fill="none" />
              <path d="M8 23h10a7 7 0 000-14h-2" stroke="var(--landing-text-primary)" strokeWidth="3" strokeLinecap="round" fill="none" />
            </svg>
            <span className="text-2xl font-bold leading-none" style={{ color: 'var(--landing-text-primary)' }}>Sardis</span>
          </a>
          <a href="/login" className="text-sm font-medium text-white rounded-lg px-4 py-2" style={{ backgroundColor: 'var(--landing-accent)' }}>Sign In</a>
        </div>
      </div>
    </nav>
  );
}
import Hero from '@/components/landing/Hero';
import SocialProof from '@/components/landing/SocialProof';
import DashboardMockup from '@/components/landing/DashboardMockup';
import ProblemCards from '@/components/landing/ProblemCards';
import HowItWorks from '@/components/landing/HowItWorks';
import FeaturesGrid from '@/components/landing/FeaturesGrid';
import PayWithSardis from '@/components/landing/PayWithSardis';
import StatsSection from '@/components/landing/StatsSection';
import DevExperience from '@/components/landing/DevExperience';
import BuiltFor from '@/components/landing/BuiltFor';
import Marquee from '@/components/landing/Marquee';
import Protocols from '@/components/landing/Protocols';
import Integrations from '@/components/landing/Integrations';
import CTASection from '@/components/landing/CTASection';
import Footer from '@/components/landing/Footer';

// Scroll-triggered animation wrapper
function AnimatedSection({ children, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export default function LandingV2() {
  return (
    <div className="min-h-screen [font-synthesis:none]" style={{ backgroundColor: 'var(--landing-bg)' }}>

      <Navbar />

      {/* Spacer for fixed navbar */}
      <div className="h-[72px]" />

      <Hero />

      <AnimatedSection>
        <SocialProof />
      </AnimatedSection>

      <AnimatedSection>
        <DashboardMockup />
      </AnimatedSection>

      <AnimatedSection>
        <ProblemCards />
      </AnimatedSection>

      <AnimatedSection>
        <HowItWorks />
      </AnimatedSection>

      <AnimatedSection>
        <PayWithSardis />
      </AnimatedSection>

      <AnimatedSection>
        <FeaturesGrid />
      </AnimatedSection>

      <StatsSection />

      <AnimatedSection>
        <DevExperience />
      </AnimatedSection>

      <AnimatedSection>
        <BuiltFor />
      </AnimatedSection>

      <AnimatedSection>
        <Protocols />
      </AnimatedSection>

      <AnimatedSection>
        <Integrations />
      </AnimatedSection>

      <Marquee />

      {/* GEO: Internal links section for AI crawlers + SEO */}
      <section className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-16" style={{ borderTop: '1px solid var(--landing-border)' }}>
        <h2
          className="text-center mb-10 font-semibold tracking-[-0.02em]"
          style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 'clamp(22px, 3vw, 32px)', color: 'var(--landing-text-primary)' }}
        >
          Explore the Platform
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { to: '/docs/quickstart', title: 'Quickstart Guide', desc: 'Set up Sardis and make your first AI agent payment in minutes.' },
            { to: '/docs/wallets', title: 'AI Agent Wallets', desc: 'Non-custodial MPC wallets with programmable spending limits.' },
            { to: '/docs/policies', title: 'Spending Policies', desc: 'Define spending rules in natural language with a 12-check enforcement pipeline.' },
            { to: '/docs/spending-mandates', title: 'Spending Mandates', desc: 'Delegate financial authority to agents with cryptographic controls.' },
            { to: '/docs/security', title: 'Security & Audit Trail', desc: 'Append-only ledger with signed attestation envelopes and Merkle proofs.' },
            { to: '/docs/integrations', title: 'Framework Integrations', desc: 'Works with Claude MCP, OpenAI, LangChain, CrewAI, AutoGPT, and more.' },
            { to: '/docs/ap2', title: 'AP2 Protocol', desc: 'Industry-standard Agent Payment Protocol by Google, PayPal, Mastercard, and Visa.' },
            { to: '/docs/mcp-server', title: 'MCP Server', desc: '52 tools for Claude Desktop — wallets, payments, treasury, and compliance.' },
            { to: '/docs/faq', title: 'FAQ', desc: 'Frequently asked questions about AI agent payments and Sardis.' },
          ].map((item) => (
            <Link
              key={item.to}
              href={item.to}
              className="block rounded-lg p-5 transition-colors"
              style={{ border: '1px solid var(--landing-border)', backgroundColor: 'transparent' }}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--landing-accent)'}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--landing-border)'}
            >
              <h3
                className="font-medium mb-1.5"
                style={{ fontFamily: "'Inter', sans-serif", fontSize: '15px', color: 'var(--landing-text-primary)' }}
              >
                {item.title}
              </h3>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', color: 'var(--landing-text-ghost)', lineHeight: '1.5' }}>
                {item.desc}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <AnimatedSection>
        <CTASection />
      </AnimatedSection>

      <Footer />
    </div>
  );
}
