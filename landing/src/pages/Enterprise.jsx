import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Sun, Moon, Check, Shield, Lock, TrendingUp, Activity, FileText, Clock, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import SardisLogo from "../components/SardisLogo";
import WaitlistModal from "../components/WaitlistModal";

// Isometric Icons
const icons = {
  terminal: "/icons/terminal-1.png",
  rocketLaunch: "/icons/rocket-launch-2.png",
  handshake: "/icons/handshake-3.png",
  verifiedUser: "/icons/verified-user-4.png",
  policy: "/icons/policy-5.png",
  shieldLock: "/icons/shield-lock-6.png",
  trendingUp: "/icons/trending-up-7.png",
  wallet: "/icons/wallet-8.png",
  searchInsights: "/icons/search-insights-9.png",
  creditCardGear: "/icons/credit-card-gear-10.png",
  autoRenew: "/icons/auto-renew-0.png",
};

// Animation Variants
const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

// Dark Mode Toggle
function DarkModeToggle({ isDark, toggle }) {
  return (
    <button
      onClick={toggle}
      className="w-10 h-10 border border-border hover:border-[var(--sardis-orange)] transition-colors flex items-center justify-center"
      aria-label="Toggle dark mode"
    >
      {isDark ? (
        <Sun className="w-5 h-5 text-[var(--sardis-orange)]" />
      ) : (
        <Moon className="w-5 h-5 text-foreground" />
      )}
    </button>
  );
}

// Icon Component for isometric PNGs
function IsometricIcon({ src, alt = "", className = "", isDark = true }) {
  return (
    <img
      src={src}
      alt={alt}
      className={cn("w-8 h-8 object-contain", className)}
      style={{
        filter: isDark
          ? "drop-shadow(0 0 1px rgba(0,0,0,0.3))"
          : "invert(1) drop-shadow(0 0 1px rgba(255,255,255,0.3))"
      }}
    />
  );
}

function Enterprise() {
  const [scrolled, setScrolled] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    if (savedTheme === "dark" || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    } else {
      setIsDark(false);
      document.documentElement.classList.remove("dark");
    }
  }, []);

  const toggleDarkMode = () => {
    setIsDark(!isDark);
    if (isDark) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden font-sans selection:bg-primary/20">

      {/* Navigation */}
      <nav
        className={cn(
          "fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b",
          scrolled ? "bg-background/95 backdrop-blur-sm border-border py-3" : "py-6 bg-transparent border-transparent"
        )}
      >
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
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none" asChild>
              <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </Button>
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <Button
              className="ml-2 bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20"
              onClick={() => setIsWaitlistOpen(true)}
            >
              Book a Demo
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-28 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 -right-32 w-96 h-96 bg-[var(--sardis-orange)]/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 -left-32 w-80 h-80 bg-[var(--sardis-teal)]/5 rounded-full blur-3xl" />
        </div>

        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial="initial"
            animate="animate"
            variants={staggerContainer}
            className="max-w-4xl mx-auto text-center"
          >
            <motion.h1 variants={fadeInUp} className="text-5xl md:text-6xl lg:text-7xl font-display font-bold leading-[1.05] tracking-tight mb-6">
              Give Your AI Agents a Corporate Wallet — With{" "}
              <span className="text-[var(--sardis-orange)]">CFO-Grade Controls</span>
            </motion.h1>

            <motion.p variants={fadeInUp} className="text-lg md:text-xl text-muted-foreground mb-10 max-w-3xl mx-auto leading-relaxed">
              83% of enterprises deploy AI agents. Zero have policy-controlled payment infrastructure. Until now.
            </motion.p>

            <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                size="lg"
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Book a Demo
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-border hover:border-[var(--sardis-orange)] rounded-none px-8 py-6 text-lg"
                asChild
              >
                <Link to="/docs">View Documentation</Link>
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Separator */}
      <div className="relative h-px w-full">
        <div className="absolute inset-0 bg-border" />
        <div className="absolute left-1/2 -translate-x-1/2 -top-3 bg-background px-4">
          <div className="w-4 h-4 bg-[var(--sardis-orange)] rotate-45" />
        </div>
      </div>

      {/* Problem Section */}
      <section className="py-28 md:py-36 relative">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-destructive tracking-[0.08em] font-bold mb-4 uppercase">The $10.91B Problem</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6 leading-tight">AI Agents Need to Spend Money</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              But your current infrastructure was built for humans, not autonomous systems.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: icons.searchInsights,
                title: "Zero Per-Agent Visibility",
                description: "Shared corporate cards mean you cannot track which agent spent what. Finance teams are flying blind."
              },
              {
                icon: icons.policy,
                title: "Inflexible Limits",
                description: "Hard-coded spending caps do not adapt to context. Your agents need dynamic, policy-driven controls."
              },
              {
                icon: icons.shieldLock,
                title: "Compliance Nightmare",
                description: "No audit trail means failed SOC2 audits. Every transaction needs provenance and accountability."
              },
              {
                icon: icons.autoRenew,
                title: "Manual Approval Bottlenecks",
                description: "Humans in the loop slow down agents. You need automated guardrails, not approval queues."
              }
            ].map((problem, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-destructive transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="w-14 h-14 border border-border flex items-center justify-center mb-4 group-hover:border-destructive transition-colors">
                      <IsometricIcon src={problem.icon} className="w-9 h-9" isDark={isDark} />
                    </div>
                    <CardTitle className="text-lg font-semibold font-display">{problem.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">
                      {problem.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-28 md:py-36 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">How It Works</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Four Steps to Financial Autonomy</h2>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            {[
              {
                step: "01",
                icon: icons.policy,
                title: "Natural Language Policies",
                description: "Define spending rules in plain English: 'Max $500/day for API services, only approved vendors.' No DSL, no complex syntax.",
                example: '"Max $1000/week for cloud compute, SaaS only, weekdays 9-5 EST"'
              },
              {
                step: "02",
                icon: icons.creditCardGear,
                title: "Per-Agent Virtual Cards",
                description: "Each agent gets its own Visa card with granular spending controls. Track every transaction back to the agent that made it.",
                example: "Agent-Research-01 → Card ****4532 → $45.00 @ OpenAI API"
              },
              {
                step: "03",
                icon: icons.searchInsights,
                title: "Real-Time Dashboard",
                description: "See every transaction as it happens. Detect anomalies instantly. Get alerts when agents approach policy limits.",
                example: "Alert: Agent-Outreach-05 at 87% of daily limit ($870/$1000)"
              },
              {
                step: "04",
                icon: icons.shieldLock,
                title: "Compliance Reports",
                description: "SOC2-ready audit trails, one click away. Every transaction logged on an append-only ledger with full provenance.",
                example: "Export: Q1 2026 Agent Spending Report (CSV, JSON, PDF)"
              }
            ].map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="flex items-start gap-4 mb-4">
                      <div className="w-12 h-12 border-2 border-[var(--sardis-orange)] bg-background flex items-center justify-center font-mono font-bold text-sm text-[var(--sardis-orange)]">
                        {step.step}
                      </div>
                      <div className="w-14 h-14 border border-border flex items-center justify-center group-hover:border-[var(--sardis-orange)] transition-colors">
                        <IsometricIcon src={step.icon} className="w-9 h-9" isDark={isDark} />
                      </div>
                    </div>
                    <CardTitle className="text-xl font-semibold font-display">{step.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-muted-foreground leading-relaxed">
                      {step.description}
                    </p>
                    <div className="p-3 bg-muted border border-border font-mono text-sm">
                      {step.example}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Integration Showcase */}
      <section className="py-28 md:py-36 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-teal-strong)] dark:text-[#9DD9D2] tracking-[0.08em] font-bold mb-4 uppercase">Integrations</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Works With Every Major AI Framework</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              65+ MCP tools, 5 blockchain networks, 9 framework integrations. Your agents, your stack.
            </p>
          </div>

          {/* Logo Grid */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-6 mb-12"
          >
            {[
              { name: "LangChain", logo: "/icons/langchain.svg" },
              { name: "CrewAI", logo: "/icons/openai-2.svg" },
              { name: "OpenAI", logo: "/icons/openai-2.svg" },
              { name: "Gemini", logo: "/icons/gemini.svg" },
              { name: "Claude", logo: "/icons/mcp.svg" },
              { name: "Vercel AI", logo: "/icons/vercel.svg" },
              { name: "Salesforce", logo: "/icons/handshake-3.png" },
              { name: "ServiceNow", logo: "/icons/terminal-1.png" },
            ].map((integration, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="flex items-center justify-center p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors"
              >
                <img
                  src={integration.logo}
                  alt={integration.name}
                  className="w-12 h-12 object-contain"
                  style={{ filter: isDark ? 'invert(1)' : 'none' }}
                />
              </motion.div>
            ))}
          </motion.div>

          <div className="text-center">
            <Badge variant="outline" className="text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">
              65+ MCP TOOLS • 5 BLOCKCHAIN NETWORKS • 9 FRAMEWORK INTEGRATIONS
            </Badge>
          </div>
        </div>
      </section>

      {/* Trust & Security */}
      <section className="py-28 md:py-36 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">Trust & Security</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Enterprise-Grade Security</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Non-custodial infrastructure with compliance-first architecture.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Lock,
                title: "Non-Custodial",
                description: "We never hold your money. MPC signing ensures no single entity can move funds without authorization.",
                badge: "Zero Trust"
              },
              {
                icon: Shield,
                title: "Know Your Agent (KYA)",
                description: "ERC-8004 on-chain identity, behavioral fingerprinting, and confidence-based routing. Trust scoring for every agent.",
                badge: "AI-Native"
              },
              {
                icon: FileText,
                title: "Compliance Reports",
                description: "5 report types (SOX, SOC2, PCI-DSS, GDPR, custom). Automated generation with CSV/HTML export.",
                badge: "Audit-Ready"
              },
              {
                icon: Activity,
                title: "Merkle Audit Trail",
                description: "Tamper-proof ledger anchored to Base blockchain via Merkle trees. Cryptographic proof of every transaction.",
                badge: "Immutable"
              }
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
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
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-28 md:py-36 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">Pricing</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Built for Teams of All Sizes</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Start free in sandbox mode. Scale to production when you are ready.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {[
              {
                name: "Starter",
                price: "$0",
                period: "/month",
                description: "Perfect for testing and development",
                features: [
                  "Sandbox environment",
                  "100 transactions/month",
                  "2 agents",
                  "Basic policies",
                  "Email support",
                  "Community access"
                ],
                cta: "Start Free",
                highlight: false
              },
              {
                name: "Growth",
                price: "$99",
                period: "/month",
                description: "For teams deploying production agents",
                features: [
                  "10,000 transactions/month",
                  "10 agents",
                  "Virtual cards (Stripe/Lithic)",
                  "Spending analytics + anomaly detection",
                  "Natural language policies",
                  "Guardrails & circuit breakers",
                  "Priority support",
                  "SLA: 99.5%"
                ],
                cta: "Book a Demo",
                highlight: true
              },
              {
                name: "Enterprise",
                price: "Custom",
                period: "",
                description: "For mission-critical deployments",
                features: [
                  "Unlimited transactions",
                  "Unlimited agents",
                  "Multi-tenant orgs + RBAC",
                  "A2A escrow & settlement",
                  "Merkle audit anchoring",
                  "Goal drift detection",
                  "Plugin system",
                  "Dedicated support",
                  "SLA: 99.9%",
                  "Private deployment"
                ],
                cta: "Contact Sales",
                highlight: false
              }
            ].map((tier, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className={cn(
                  "h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none relative",
                  tier.highlight && "border-[var(--sardis-orange)] border-2"
                )}>
                  {tier.highlight && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <Badge className="bg-[var(--sardis-orange)] text-white rounded-none font-mono">
                        MOST POPULAR
                      </Badge>
                    </div>
                  )}
                  <CardHeader className="text-center pb-6">
                    <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider mb-2">{tier.name}</p>
                    <div className="mb-2">
                      <span className="text-4xl font-bold font-display">{tier.price}</span>
                      <span className="text-muted-foreground">{tier.period}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{tier.description}</p>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ul className="space-y-3">
                      {tier.features.map((feature, j) => (
                        <li key={j} className="flex items-start gap-3 text-sm">
                          <Check className="w-5 h-5 text-[var(--sardis-orange)] shrink-0 mt-0.5" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button
                      className={cn(
                        "w-full rounded-none font-semibold",
                        tier.highlight
                          ? "bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90"
                          : "border-border hover:border-[var(--sardis-orange)]"
                      )}
                      variant={tier.highlight ? "default" : "outline"}
                      onClick={() => setIsWaitlistOpen(true)}
                    >
                      {tier.cta}
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-28 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="max-w-3xl mx-auto"
          >
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6">
              Ready to Give Your Agents Financial Autonomy?
            </h2>
            <p className="text-lg text-muted-foreground mb-10">
              Join enterprises deploying AI agents with policy-controlled payment infrastructure.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button
                size="lg"
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Book a Demo
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-border hover:border-[var(--sardis-orange)] rounded-none px-8 py-6 text-lg"
                onClick={() => setIsWaitlistOpen(true)}
              >
                Start Free
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-start gap-8 mb-8">
            <Link to="/" className="flex items-center gap-3">
              <SardisLogo size="small" />
              <span className="font-bold font-display">Sardis</span>
            </Link>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Product</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><Link to="/docs" className="hover:text-[var(--sardis-orange)] transition-colors">Documentation</Link></li>
                  <li><Link to="/docs/quickstart" className="hover:text-[var(--sardis-orange)] transition-colors">Quick Start</Link></li>
                  <li><Link to="/playground" className="hover:text-[var(--sardis-orange)] transition-colors">Playground</Link></li>
                  <li><Link to="/enterprise" className="hover:text-[var(--sardis-orange)] transition-colors">Enterprise</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Resources</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><Link to="/docs/blog" className="hover:text-[var(--sardis-orange)] transition-colors">Blog</Link></li>
                  <li><Link to="/docs/changelog" className="hover:text-[var(--sardis-orange)] transition-colors">Changelog</Link></li>
                  <li><Link to="/docs/security" className="hover:text-[var(--sardis-orange)] transition-colors">Security</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Legal</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><Link to="/docs/terms" className="hover:text-[var(--sardis-orange)] transition-colors">Terms</Link></li>
                  <li><Link to="/docs/privacy" className="hover:text-[var(--sardis-orange)] transition-colors">Privacy</Link></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Connect</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noreferrer" className="hover:text-[var(--sardis-orange)] transition-colors">GitHub</a></li>
                  <li><a href="https://x.com/sardisHQ" target="_blank" rel="noreferrer" className="hover:text-[var(--sardis-orange)] transition-colors">X (Twitter)</a></li>
                  <li><a href="mailto:contact@sardis.sh" className="hover:text-[var(--sardis-orange)] transition-colors">Contact</a></li>
                </ul>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-border text-center text-xs text-muted-foreground font-mono">
            © 2026 Sardis. All rights reserved.
          </div>
        </div>
      </footer>

      {/* Waitlist Modal */}
      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </div>
  );
}

export default Enterprise;
