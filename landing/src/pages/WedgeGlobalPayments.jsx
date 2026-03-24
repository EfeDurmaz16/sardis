import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Sun, Moon, Globe, Clock, DollarSign, FileCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import SardisLogo from "../components/SardisLogo";
import WaitlistModal from "../components/WaitlistModal";
import SEO, { createBreadcrumbSchema } from "@/components/SEO";

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 }
};

const staggerContainer = {
  animate: { transition: { staggerChildren: 0.1 } }
};

function DarkModeToggle({ isDark, toggle }) {
  return (
    <button
      onClick={toggle}
      className="w-10 h-10 border border-border hover:border-[var(--sardis-orange)] transition-colors flex items-center justify-center"
      aria-label="Toggle dark mode"
    >
      {isDark ? <Sun className="w-5 h-5 text-[var(--sardis-orange)]" /> : <Moon className="w-5 h-5 text-foreground" />}
    </button>
  );
}

function WedgeGlobalPayments() {
  const [scrolled, setScrolled] = useState(false);
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    return saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches);
  });
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  const toggleDarkMode = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden font-sans selection:bg-primary/20">
      <SEO
        title="US to EU Cross-Border Payments in 30 Seconds"
        description="Cross-border payments at the speed of stablecoins. USDC to EURC atomic swap. 5-15 bps vs 1-3% SWIFT fees. MiCA compliant."
        path="/wedge/global-payments"
        schemas={[createBreadcrumbSchema([{ name: "Home", href: "/" }, { name: "Global Payments" }])]}
      />

      {/* Navigation */}
      <nav className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b",
        scrolled ? "bg-background/95 backdrop-blur-sm border-border py-3" : "py-6 bg-transparent border-transparent"
      )}>
        <div className="container mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 font-bold text-xl tracking-tight font-display">
            <SardisLogo />
            <span>Sardis</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none" asChild>
              <Link to="/docs">Docs</Link>
            </Button>
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none" asChild>
              <Link to="/enterprise">Enterprise</Link>
            </Button>
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <Button
              className="ml-2 bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20"
              onClick={() => setIsWaitlistOpen(true)}
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-28 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 -right-32 w-96 h-96 bg-[var(--sardis-orange)]/5 rounded-full blur-3xl" />
        </div>
        <div className="container mx-auto px-6 relative z-10">
          <motion.div initial="initial" animate="animate" variants={staggerContainer} className="max-w-4xl mx-auto text-center">
            <motion.div variants={fadeInUp}>
              <Badge variant="outline" className="text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono mb-6">
                WEDGE C: CROSS-BORDER PAYMENTS
              </Badge>
            </motion.div>
            <motion.h1 variants={fadeInUp} className="text-5xl md:text-6xl lg:text-7xl font-display font-bold leading-[1.05] tracking-tight mb-6">
              Cross-Border Payments at
              <br />
              <span className="text-[var(--sardis-orange)]">the Speed of Stablecoins</span>
            </motion.h1>
            <motion.p variants={fadeInUp} className="text-lg md:text-xl text-muted-foreground mb-10 max-w-3xl mx-auto leading-relaxed">
              US to EU in 30 seconds. USDC to EURC atomic swap across 3 venues.
              5-15 basis points total cost vs. 1-3% SWIFT fees. MiCA compliant from day one.
            </motion.p>
            <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                size="lg"
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Get Started — 0.5% of Volume
              </Button>
              <Button size="lg" variant="outline" className="border-border hover:border-[var(--sardis-orange)] rounded-none px-8 py-6 text-lg" asChild>
                <Link to="/docs">View Documentation</Link>
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-28 md:py-36 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-destructive tracking-[0.08em] font-bold mb-4 uppercase">SWIFT vs. Sardis</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">The Numbers Speak</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <Card className="bg-card border-border rounded-none">
              <CardHeader>
                <CardTitle className="text-2xl font-display text-destructive">SWIFT / Wire Transfer</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between py-2 border-b border-border"><span className="text-muted-foreground">Settlement time</span><span className="font-mono font-bold">2-3 business days</span></div>
                <div className="flex justify-between py-2 border-b border-border"><span className="text-muted-foreground">FX fees</span><span className="font-mono font-bold">1-3%</span></div>
                <div className="flex justify-between py-2 border-b border-border"><span className="text-muted-foreground">Wire fee</span><span className="font-mono font-bold">$25-50 per transfer</span></div>
                <div className="flex justify-between py-2"><span className="text-muted-foreground">Compliance</span><span className="font-mono font-bold">Manual</span></div>
              </CardContent>
            </Card>
            <Card className="bg-card border-[var(--sardis-orange)] rounded-none">
              <CardHeader>
                <CardTitle className="text-2xl font-display text-[var(--sardis-orange)]">Sardis (USDC/EURC)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between py-2 border-b border-border"><span className="text-muted-foreground">Settlement time</span><span className="font-mono font-bold text-[var(--sardis-orange)]">1.5 seconds</span></div>
                <div className="flex justify-between py-2 border-b border-border"><span className="text-muted-foreground">FX fees</span><span className="font-mono font-bold text-[var(--sardis-orange)]">5-15 bps</span></div>
                <div className="flex justify-between py-2 border-b border-border"><span className="text-muted-foreground">Wire fee</span><span className="font-mono font-bold text-[var(--sardis-orange)]">$0 (gas only)</span></div>
                <div className="flex justify-between py-2"><span className="text-muted-foreground">Compliance</span><span className="font-mono font-bold text-[var(--sardis-orange)]">Automated (MiCA)</span></div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-28 md:py-36 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-teal-strong)] dark:text-[#9DD9D2] tracking-[0.08em] font-bold mb-4 uppercase">Features</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Built for Treasury Teams</h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Globe, title: "USDC/EURC Atomic Swap", description: "3 FX venues: Tempo DEX, Uniswap V3, Circle Mint. Best price auto-selected. Atomic execution — no partial fills.", badge: "3 Venues" },
              { icon: Clock, title: "1.5-Second Settlement", description: "On-chain finality in seconds. No correspondent banking delays. No weekend cutoffs. 24/7/365 settlement.", badge: "Real-Time" },
              { icon: DollarSign, title: "5-15 bps Total Cost", description: "Compare to 100-300 bps on SWIFT. No intermediary bank fees. No hidden FX markups. Transparent on-chain pricing.", badge: "90% Savings" },
              { icon: FileCheck, title: "MiCA Compliance", description: "EU CASP tracking, Article 66 reporting, 72-hour SAR filing. KYB, AML/sanctions, and travel rule built in.", badge: "EU Ready" },
            ].map((feature, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}>
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group relative">
                  <div className="absolute top-3 right-3">
                    <Badge className="bg-[var(--sardis-orange)]/10 text-[var(--sardis-orange)] border border-[var(--sardis-orange)]/30 rounded-none text-xs font-mono">
                      {feature.badge}
                    </Badge>
                  </div>
                  <CardHeader className="pb-3">
                    <div className="w-14 h-14 border border-border flex items-center justify-center mb-4 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <feature.icon className="w-7 h-7 text-[var(--sardis-orange)]" />
                    </div>
                    <CardTitle className="text-lg font-semibold font-display">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-28 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6 text-center">
          <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="max-w-3xl mx-auto">
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6">Skip SWIFT. Settle in Seconds.</h2>
            <p className="text-lg text-muted-foreground mb-10">
              Your treasury deposits USDC, sets a mandate, and Sardis handles FX, settlement, and compliance automatically.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                size="lg"
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Get Started — 0.5% of Volume
              </Button>
              <Button size="lg" variant="outline" className="border-border hover:border-[var(--sardis-orange)] rounded-none px-8 py-6 text-lg" asChild>
                <Link to="/docs">Read the Docs</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="container mx-auto px-6 text-center text-xs text-muted-foreground font-mono">
          2026 Sardis Labs, Inc. All rights reserved.
        </div>
      </footer>

      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </div>
  );
}

export default WedgeGlobalPayments;
