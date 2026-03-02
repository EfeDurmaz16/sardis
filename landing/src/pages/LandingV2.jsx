import { useState } from 'react';
import { motion } from 'framer-motion';

// Font imports (fix latent bug - these packages are installed but never imported)
import '@fontsource/space-grotesk/400.css';
import '@fontsource/space-grotesk/500.css';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/inter/300.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/jetbrains-mono/400.css';

// Section components
import Navbar from '@/components/landing/Navbar';
import Hero from '@/components/landing/Hero';
import SocialProof from '@/components/landing/SocialProof';
import DashboardMockup from '@/components/landing/DashboardMockup';
import ProblemCards from '@/components/landing/ProblemCards';
import HowItWorks from '@/components/landing/HowItWorks';
import FeaturesGrid from '@/components/landing/FeaturesGrid';
import StatsSection from '@/components/landing/StatsSection';
import DevExperience from '@/components/landing/DevExperience';
import BuiltFor from '@/components/landing/BuiltFor';
import Marquee from '@/components/landing/Marquee';
import Protocols from '@/components/landing/Protocols';
import Integrations from '@/components/landing/Integrations';
import CTASection from '@/components/landing/CTASection';
import Footer from '@/components/landing/Footer';
import WaitlistModal from '@/components/WaitlistModal';
import SEO from '@/components/SEO';

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
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <div className="min-h-screen [font-synthesis:none]" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <SEO
        title="Sardis: The Payment OS for the Agent Economy"
        description="AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust. Non-custodial wallets, spending policies, multi-chain payments."
      />

      <Navbar onOpenWaitlist={() => setWaitlistOpen(true)} />

      {/* Spacer for fixed navbar */}
      <div className="h-[72px]" />

      <Hero onOpenWaitlist={() => setWaitlistOpen(true)} />

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

      <AnimatedSection>
        <CTASection onOpenWaitlist={() => setWaitlistOpen(true)} />
      </AnimatedSection>

      <Footer />

      <WaitlistModal
        isOpen={waitlistOpen}
        onClose={() => setWaitlistOpen(false)}
      />
    </div>
  );
}
