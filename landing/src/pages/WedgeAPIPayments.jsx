import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Sun, Moon, Zap, Shield, CreditCard, BarChart3 } from "lucide-react";
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

function WedgeAPIPayments() {
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
        title="Automated API Payments for AI Agents"
        description="Your AI assistant wants to pay. Let it. HTTP 402 auto-pay, virtual cards, spending limits — all policy-controlled."
        path="/wedge/api-payments"
        schemas={[createBreadcrumbSchema([{ name: "Home", href: "/" }, { name: "API Payments" }])]}
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
                WEDGE B: AUTOMATED API PAYMENTS
              </Badge>
            </motion.div>
            <motion.h1 variants={fadeInUp} className="text-5xl md:text-6xl lg:text-7xl font-display font-bold leading-[1.05] tracking-tight mb-6">
              Your Assistant Wants to Pay.
              <br />
              <span className="text-[var(--sardis-orange)]">Let It.</span>
            </motion.h1>
            <motion.p variants={fadeInUp} className="text-lg md:text-xl text-muted-foreground mb-10 max-w-3xl mx-auto leading-relaxed">
              AI agents consume APIs programmatically. Stripe checkout does not work when the customer is a GPT-4 agent.
              Sardis handles HTTP 402 auto-pay, virtual cards, and spending limits — all policy-controlled.
            </motion.p>
            <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                size="lg"
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Start at $199/mo
              </Button>
              <Button size="lg" variant="outline" className="border-border hover:border-[var(--sardis-orange)] rounded-none px-8 py-6 text-lg" asChild>
                <Link to="/docs/quickstart">View Quickstart</Link>
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-28 md:py-36 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">How It Works</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">API Returns 402. Agent Pays. You Earn.</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { step: "01", title: "API Returns HTTP 402", description: "Your API returns a 402 Payment Required response with a Sardis payment header. One line of code on your server." },
              { step: "02", title: "Agent Wallet Auto-Pays", description: "The agent's Sardis wallet detects the 402, checks the spending mandate, and pays automatically. Policy-checked and audited." },
              { step: "03", title: "You Receive Settlement", description: "USDC settlement in real-time to your wallet. Full transaction log in your Sardis dashboard. AML-screened automatically." },
            ].map((item, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: i * 0.1 }}>
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="w-12 h-12 border-2 border-[var(--sardis-orange)] bg-background flex items-center justify-center font-mono font-bold text-sm text-[var(--sardis-orange)] mb-4">
                      {item.step}
                    </div>
                    <CardTitle className="text-xl font-semibold font-display">{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">{item.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-28 md:py-36 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-teal-strong)] dark:text-[#9DD9D2] tracking-[0.08em] font-bold mb-4 uppercase">Features</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Everything for Agent-to-API Payments</h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Zap, title: "MPP x402 Auto-Pay", description: "Stripe Merchant Payment Protocol integration. HTTP 402 triggers automatic wallet payment. No checkout page needed.", badge: "MPP Native" },
              { icon: CreditCard, title: "Virtual Cards", description: "Single-use Visa cards from USDC via Laso. Agent buys SaaS on any legacy checkout flow. $1/card + 0.5%.", badge: "Fiat Bridge" },
              { icon: Shield, title: "Spending Limits", description: "NLP mandates: 'max $500/day on dev tools.' 12-check policy pipeline before every payment. Non-custodial MPC signing.", badge: "Policy Engine" },
              { icon: BarChart3, title: "Real-Time Dashboard", description: "Every transaction logged with cryptographic proof. Merkle-anchored audit trail. AML screening on every payment.", badge: "Audit Ready" },
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
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6">Monetize Your API for AI Agents</h2>
            <p className="text-lg text-muted-foreground mb-10">
              50K agents already have Sardis wallets. Integrated with Stripe MPP (early access).
              0.5% facilitator fee on transactions. No monthly minimum.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                size="lg"
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Start at $199/mo
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

export default WedgeAPIPayments;
