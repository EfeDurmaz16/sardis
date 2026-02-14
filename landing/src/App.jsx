import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import SardisPlayground from "./components/SardisPlayground";
import WaitlistForm from "./components/WaitlistForm";
import SardisLogo from "./components/SardisLogo";
import WaitlistModal from "./components/WaitlistModal";

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

// Copy Command Component
function CopyCommand({ command }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      onClick={handleCopy}
      className="group cursor-pointer flex items-center gap-3 px-5 py-3 bg-[var(--sardis-ink)] dark:bg-[#1f1e1c] border border-border hover:border-[var(--sardis-orange)] transition-all duration-200 font-mono text-sm"
    >
      <img src={icons.terminal} alt="" className="w-5 h-5" />
      <code className="text-[var(--sardis-canvas)] group-hover:text-white transition-colors">{command}</code>
      <div className="ml-2 px-2 py-1 border border-[var(--sardis-canvas)]/20 group-hover:border-[var(--sardis-orange)] transition-colors">
        {copied ? (
          <span className="text-emerald-400 text-xs font-bold">COPIED</span>
        ) : (
          <span className="text-[var(--sardis-canvas)]/60 group-hover:text-[var(--sardis-orange)] text-xs font-bold">COPY</span>
        )}
      </div>
    </div>
  );
}

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

// Icon Component for isometric PNGs with contrast fix
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

function App() {
  const [scrolled, setScrolled] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [isWaitlistOpen, setIsWaitlistOpen] = useState(false);

  useEffect(() => {
    // Check for saved preference or system preference
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
          <div className="flex items-center gap-3 font-bold text-xl tracking-tight font-display">
            <SardisLogo />
            <span>Sardis</span>
          </div>

          <div className="hidden md:flex items-center gap-1">
            <Badge variant="outline" className="mr-6 border-emerald-600 text-emerald-600 dark:text-emerald-400 dark:border-emerald-400 bg-transparent px-3 py-1 rounded-none">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 animate-pulse" />
              LIVE ON TESTNET • 3.5K+ INSTALLS
            </Badge>
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none" asChild>
              <Link to="/docs">Docs</Link>
            </Button>
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none" asChild>
              <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </Button>
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <Button
              className="ml-2 bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-medium rounded-none"
              onClick={() => setIsWaitlistOpen(true)}
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-48 md:pb-32 overflow-hidden">
        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial="initial"
            animate="animate"
            variants={staggerContainer}
            className="max-w-4xl mx-auto text-center"
          >
            <motion.div variants={fadeInUp} className="flex justify-center mb-8">
              <Badge variant="outline" className="px-4 py-1.5 rounded-none text-sm font-mono font-medium border-border bg-transparent">
                Building the $30 Trillion Machine Customer Economy
              </Badge>
            </motion.div>

            <motion.h1 variants={fadeInUp} className="text-5xl md:text-7xl font-display font-bold leading-tight tracking-tight mb-8">
              The Payment OS for the <span className="text-[var(--sardis-orange)]">Agent Economy</span>
            </motion.h1>

            <motion.p variants={fadeInUp} className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
              Prevent Financial Hallucinations. Give your agents non-custodial MPC wallets with natural language spending limits.
            </motion.p>

            <motion.div variants={fadeInUp} className="flex flex-col items-center gap-4">
              <CopyCommand command="npx @sardis/mcp-server init --mode simulated && npx @sardis/mcp-server start" />
              <div className="flex flex-col sm:flex-row items-center gap-4 mt-4">
                <Button
                  size="lg"
                  className="h-14 px-8 text-lg rounded-none bg-[var(--sardis-orange)] hover:bg-[var(--sardis-orange)]/90 text-white font-medium"
                  onClick={() => setIsWaitlistOpen(true)}
                >
                  Get Started
                  <span className="ml-2">→</span>
                </Button>
                <Button size="lg" variant="outline" className="h-14 px-8 text-lg rounded-none border-border hover:border-[var(--sardis-orange)] hover:text-[var(--sardis-orange)]" asChild>
                  <Link to="/docs">View Docs</Link>
                </Button>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Separator */}
      <div className="h-px bg-border w-full" />

      {/* Problem Section: The Read-Only Trap */}
      <section className="py-24 relative">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <h2 className="text-3xl md:text-4xl font-display font-bold mb-6">The "Read-Only" Trap</h2>
              <p className="text-xl text-muted-foreground mb-6 leading-relaxed">
                We are transitioning to an Agentic Economy, yet AI agents remain "read-only."
              </p>
              <p className="text-xl text-muted-foreground mb-8 leading-relaxed">
                They can plan complex workflows but <strong className="text-foreground font-medium">fail at checkout</strong> because current payment rails (2FA, OTPs, CAPTCHAs) block non-human actors.
              </p>

              <ul className="space-y-4">
                {[
                  { text: "Agents get blocked by SMS 2FA", icon: icons.shieldLock },
                  { text: "No spending limits or guardrails", icon: icons.policy },
                  { text: "Impossible to audit agent spending", icon: icons.searchInsights }
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-lg text-destructive">
                    <div className="w-10 h-10 border border-destructive/30 flex items-center justify-center">
                      <IsometricIcon src={item.icon} className="w-6 h-6" isDark={isDark} />
                    </div>
                    {item.text}
                  </li>
                ))}
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              className="relative"
            >
              {/* Visual representation of the trap - A blocked terminal */}
              <div className="border border-border bg-card overflow-hidden">
                <div className="bg-muted px-4 py-3 border-b border-border flex gap-2">
                  <div className="w-3 h-3 bg-destructive" />
                  <div className="w-3 h-3 bg-yellow-500" />
                  <div className="w-3 h-3 bg-emerald-500" />
                </div>
                <div className="p-6 font-mono text-sm leading-relaxed bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] text-[var(--sardis-canvas)]">
                  <div className="text-emerald-400 mb-2">$ agent plan trip --budget 500</div>
                  <div className="text-[var(--sardis-canvas)]/60 mb-4">{`> Planning itinerary... Done.`}</div>
                  <div className="text-emerald-400 mb-2">$ agent book flights</div>
                  <div className="text-[var(--sardis-canvas)]/60 mb-4">{`> Selecting best flight... UA445 selected.`}</div>
                  <div className="text-[var(--sardis-canvas)]/60 mb-2">{`> Entering payment details...`}</div>
                  <div className="text-red-400 bg-red-500/10 p-3 border border-red-500/30">
                    {`ERROR: 2FA Required. Please enter the code sent to +1 (555) ***-****`}
                    <br />
                    {`> Timeout. Booking failed.`}
                  </div>
                </div>
              </div>

              {/* Floating badge */}
              <div className="absolute -bottom-4 -left-4 bg-destructive text-white px-4 py-2 font-mono font-bold text-sm border border-destructive">
                EXECUTION BLOCKED
              </div>
            </motion.div>
          </div>

          {/* Playground Section */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-24 max-w-5xl mx-auto"
          >
            <div className="text-center mb-10">
              <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">INTERACTIVE DEMO</Badge>
              <h3 className="text-3xl font-bold font-display">Experience the Spending Firewall</h3>
            </div>
            <SardisPlayground />
          </motion.div>
        </div>
      </section>

      {/* Features Section: Banking for Bots */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">Banking for Bots</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Sardis issues <span className="text-foreground font-medium">non-custodial</span> programmable wallets and virtual cards purpose-built for AI agents.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: icons.autoRenew,
                title: "Autonomous Execution",
                description: "Bypass human-centric 2FA barriers with MPC-secured signing. Agents can finally pay."
              },
              {
                icon: icons.policy,
                title: "Policy Engine",
                description: "Set strict limits: 'Max $50/tx, $500/day, only these merchants.' Programmable trust."
              },
              {
                icon: icons.trendingUp,
                title: "Instant Settlement",
                description: "Real-time settlement via bank transfer, virtual card, or stablecoins. No waiting days."
              },
              {
                icon: icons.shieldLock,
                title: "Human-in-the-Loop",
                description: "Payments above your threshold pause for human approval. Your agent proposes, you approve."
              },
              {
                icon: icons.autoRenew,
                title: "Goal Drift Detection",
                description: "Sardis detects when agent spending deviates from stated intent. Catch financial hallucinations before they land."
              }
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="w-16 h-16 border border-border flex items-center justify-center mb-4 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <IsometricIcon src={feature.icon} className="w-10 h-10" isDark={isDark} />
                    </div>
                    <CardTitle className="text-xl font-bold font-display">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground leading-relaxed">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Fiat Rails Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">FIAT RAILS</Badge>
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">Unified Payment Rails</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Fund agent wallets from your bank account. Pay via virtual card or stablecoins. Withdraw back to USD. One API, every rail.
            </p>
          </div>

          {/* Flow Diagram */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-12 p-8 border border-border bg-card overflow-x-auto"
          >
            <div className="flex items-center justify-center gap-4 min-w-[600px]">
              {/* Bank */}
              <div className="flex flex-col items-center gap-2">
                <div className="w-16 h-16 border-2 border-[var(--sardis-orange)] flex items-center justify-center">
                  <IsometricIcon src={icons.trendingUp} className="w-10 h-10" isDark={isDark} />
                </div>
                <span className="text-sm font-mono font-bold">Bank</span>
                <span className="text-xs text-muted-foreground">ACH / Wire / Card</span>
              </div>

              {/* Arrow */}
              <div className="flex flex-col items-center gap-1">
                <div className="h-0.5 w-12 bg-[var(--sardis-orange)]" />
                <span className="text-xs text-muted-foreground font-mono">Fund</span>
              </div>

              {/* Bridge */}
              <div className="flex flex-col items-center gap-2">
                <div className="w-16 h-16 border border-border flex items-center justify-center bg-muted">
                  <IsometricIcon src={icons.autoRenew} className="w-10 h-10" isDark={isDark} />
                </div>
                <span className="text-sm font-mono font-bold">Bridge</span>
                <span className="text-xs text-muted-foreground">Fiat ↔ USDC</span>
              </div>

              {/* Arrow */}
              <div className="flex flex-col items-center gap-1">
                <div className="h-0.5 w-12 bg-[var(--sardis-orange)]" />
                <span className="text-xs text-muted-foreground font-mono">Convert</span>
              </div>

              {/* Sardis Wallet */}
              <div className="flex flex-col items-center gap-2">
                <div className="w-20 h-20 border-2 border-[var(--sardis-orange)] flex items-center justify-center bg-[var(--sardis-orange)]/10">
                  <IsometricIcon src={icons.wallet} className="w-12 h-12" isDark={isDark} />
                </div>
                <span className="text-sm font-mono font-bold text-[var(--sardis-orange)]">Sardis Wallet</span>
                <span className="text-xs text-muted-foreground">MPC + Policy Engine</span>
              </div>

              {/* Arrow */}
              <div className="flex flex-col items-center gap-1">
                <div className="h-0.5 w-12 bg-[var(--sardis-orange)]" />
                <span className="text-xs text-muted-foreground font-mono">Spend</span>
              </div>

              {/* Outputs */}
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 border border-border flex items-center justify-center">
                    <IsometricIcon src={icons.creditCardGear} className="w-7 h-7" isDark={isDark} />
                  </div>
                  <div className="text-left">
                    <span className="text-sm font-mono font-bold block">Virtual Card</span>
                    <span className="text-xs text-muted-foreground">Pay anywhere</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 border border-border flex items-center justify-center">
                    <IsometricIcon src={icons.handshake} className="w-7 h-7" isDark={isDark} />
                  </div>
                  <div className="text-left">
                    <span className="text-sm font-mono font-bold block">Crypto</span>
                    <span className="text-xs text-muted-foreground">On-chain tx</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 border border-border flex items-center justify-center">
                    <IsometricIcon src={icons.trendingUp} className="w-7 h-7" isDark={isDark} />
                  </div>
                  <div className="text-left">
                    <span className="text-sm font-mono font-bold block">Bank Payout</span>
                    <span className="text-xs text-muted-foreground">USD withdrawal</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: icons.trendingUp,
                title: "Bank Funding",
                description: "Fund agent wallets via ACH, wire transfer, or card. Automatically converts to USDC in the wallet.",
                details: ["ACH: 0.5% fee", "Wire: 0.25% fee", "Card: 2.9% + $0.30"]
              },
              {
                icon: icons.wallet,
                title: "Unified Balance",
                description: "One wallet balance powers everything - crypto payments, virtual cards, and merchant payouts.",
                details: ["Policy enforcement on all spend", "Real-time balance tracking", "Multi-chain support"]
              },
              {
                icon: icons.creditCardGear,
                title: "USD Payouts",
                description: "Withdraw to any US bank account. Convert USDC back to USD with automatic compliance checks.",
                details: ["Same-day ACH", "2-day wire transfers", "Merchant settlements"]
              }
            ].map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="w-16 h-16 border border-border flex items-center justify-center mb-4 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <IsometricIcon src={feature.icon} className="w-10 h-10" isDark={isDark} />
                    </div>
                    <CardTitle className="text-xl font-bold font-display">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-muted-foreground leading-relaxed">
                      {feature.description}
                    </p>
                    <div className="pt-2 border-t border-border">
                      {feature.details.map((detail, j) => (
                        <div key={j} className="text-sm text-muted-foreground font-mono py-1">
                          → {detail}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Code Example */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-12 border border-border overflow-hidden"
          >
            <div className="bg-muted px-4 py-3 border-b border-border flex items-center gap-2">
              <div className="w-3 h-3 bg-destructive" />
              <div className="w-3 h-3 bg-yellow-500" />
              <div className="w-3 h-3 bg-emerald-500" />
              <span className="ml-4 text-sm font-mono text-muted-foreground">fiat-ramp.ts</span>
            </div>
            <div className="p-6 font-mono text-sm leading-relaxed bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] text-[var(--sardis-canvas)] overflow-x-auto">
              <pre className="whitespace-pre">{`import { SardisFiatRamp } from '@sardis/fiat-ramp'

const ramp = new SardisFiatRamp({
  sardisKey: 'sk_...',
  bridgeKey: 'bridge_...'
})

// Fund wallet from bank
const funding = await ramp.fundWallet({
  walletId: 'wallet_123',
  amountUsd: 1000,
  method: 'bank'  // or 'card', 'crypto'
})
console.log(funding.achInstructions) // Bank transfer details

// Withdraw to bank (policy-checked)
const withdrawal = await ramp.withdrawToBank({
  walletId: 'wallet_123',
  amountUsd: 500,
  bankAccount: { accountNumber: '...', routingNumber: '...' }
})

// Pay merchant directly in USD
const payment = await ramp.payMerchantFiat({
  walletId: 'wallet_123',
  amountUsd: 99.99,
  merchant: { name: 'ACME Corp', bankAccount: {...} }
})`}</pre>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Why Sardis Section - Competitive Positioning */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">WHY SARDIS</Badge>
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">The Policy Firewall for Agent Payments</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Others build payment rails. We build the intelligence layer that prevents financial hallucinations.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {[
              {
                icon: icons.policy,
                title: "Natural Language Policies",
                description: "Define complex spending rules in plain English. Not just limits—context-aware governance.",
                unique: true
              },
              {
                icon: icons.shieldLock,
                title: "Non-Custodial MPC",
                description: "True key ownership via Turnkey. No single entity can move funds unilaterally.",
                unique: false
              },
              {
                icon: icons.creditCardGear,
                title: "Virtual Cards",
                description: "Instant Visa cards via Lithic. Your agent can pay anywhere cards are accepted.",
                unique: true
              },
              {
                icon: icons.terminal,
                title: "Zero-Config MCP",
                description: "One command to add 46 payment tools to Claude or Cursor. No setup required.",
                unique: false
              },
              {
                icon: icons.shieldLock,
                title: "Approval Queue",
                description: "Human-in-the-loop. Agents propose, humans approve. Built into the payment flow, not bolted on.",
                unique: true
              },
              {
                icon: icons.autoRenew,
                title: "Goal Drift Guard",
                description: "AI intent vs. actual payment comparison. Catches when agents go off-script financially.",
                unique: true
              }
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group relative">
                  {item.unique && (
                    <div className="absolute top-3 right-3">
                      <Badge className="bg-[var(--sardis-orange)] text-white rounded-none text-xs font-mono">
                        UNIQUE
                      </Badge>
                    </div>
                  )}
                  <CardHeader className="pb-3">
                    <div className="w-12 h-12 border border-border flex items-center justify-center mb-3 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <IsometricIcon src={item.icon} className="w-7 h-7" isDark={isDark} />
                    </div>
                    <CardTitle className="text-lg font-bold font-display">{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {item.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Comparison callout */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5"
          >
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="text-center md:text-left">
                <h3 className="text-xl font-bold font-display mb-2">No competitor offers natural language policies + virtual cards + multi-chain</h3>
                <p className="text-muted-foreground">We analyzed Locus, Payman, and Skyfire. Read why we built Sardis differently.</p>
              </div>
              <Button variant="outline" className="rounded-none border-[var(--sardis-orange)] text-[var(--sardis-orange)] hover:bg-[var(--sardis-orange)] hover:text-white shrink-0" asChild>
                <Link to="/docs/blog/why-sardis">Read the Analysis →</Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Protocol Ecosystem Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">PROTOCOL NATIVE</Badge>
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">Built on Open Standards</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Sardis implements and extends the emerging standards for agentic commerce. Full interoperability with the protocols shaping the agent economy.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: icons.handshake,
                name: "AP2",
                fullName: "Agent Payment Protocol",
                description: "Google, PayPal, Visa consortium standard. Mandate chain verification: Intent → Cart → Payment.",
                status: "Implemented"
              },
              {
                icon: icons.wallet,
                name: "UCP",
                fullName: "Universal Commerce Protocol",
                description: "Structured checkout flows between agents and merchants. Cart management, discounts, fulfillment tracking.",
                status: "Implemented"
              },
              {
                icon: icons.rocketLaunch,
                name: "A2A",
                fullName: "Agent-to-Agent Protocol",
                description: "Multi-agent communication for payments and credential verification. Agent discovery via .well-known.",
                status: "Implemented"
              },
              {
                icon: icons.verifiedUser,
                name: "TAP",
                fullName: "Trust Anchor Protocol",
                description: "Ed25519 and ECDSA-P256 identity verification. Agent attestation and credential chains.",
                status: "Implemented"
              }
            ].map((protocol, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between mb-3">
                      <div className="w-12 h-12 border border-border flex items-center justify-center group-hover:border-[var(--sardis-orange)] transition-colors">
                        <IsometricIcon src={protocol.icon} className="w-7 h-7" isDark={isDark} />
                      </div>
                      <Badge variant="outline" className="text-emerald-600 border-emerald-600/30 rounded-none text-xs font-mono">
                        {protocol.status}
                      </Badge>
                    </div>
                    <CardTitle className="text-2xl font-bold font-display text-[var(--sardis-orange)]">{protocol.name}</CardTitle>
                    <p className="text-sm text-muted-foreground font-mono">{protocol.fullName}</p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {protocol.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* x402 Micropayments highlight */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-8 p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors"
          >
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="w-16 h-16 border border-border flex items-center justify-center">
                <IsometricIcon src={icons.creditCardGear} className="w-10 h-10" isDark={isDark} />
              </div>
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-xl font-bold font-display mb-1">x402 Micropayments</h3>
                <p className="text-muted-foreground">HTTP 402 Payment Required - Pay-per-API-call for agent services. Sub-cent transactions with instant settlement.</p>
              </div>
              <Badge variant="outline" className="text-emerald-600 border-emerald-600/30 rounded-none font-mono">
                Implemented
              </Badge>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">USE CASES</Badge>
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">What Agents Can Do</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              From simple purchases to complex multi-agent workflows, Sardis enables the full spectrum of agentic commerce.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {[
              {
                icon: icons.wallet,
                title: "Shopping Agents",
                description: "Book flights, purchase software licenses, order supplies. Agents can complete checkout flows that previously required human intervention.",
                examples: ["Travel booking", "SaaS subscriptions", "Office supplies", "API credits"]
              },
              {
                icon: icons.handshake,
                title: "Service Agents",
                description: "Pay for cloud compute, API calls, and data services. Programmatic access to any service with pay-as-you-go pricing.",
                examples: ["Cloud compute", "Data APIs", "AI model inference", "Storage services"]
              },
              {
                icon: icons.rocketLaunch,
                title: "Multi-Agent Workflows",
                description: "Coordinate payments across agent teams. One agent discovers, another negotiates, a third executes payment - all with cryptographic verification.",
                examples: ["Supply chain automation", "Research orchestration", "Content pipelines", "Trading systems"]
              },
              {
                icon: icons.verifiedUser,
                title: "Credential Verification",
                description: "Verify payment mandates, identity attestations, and capability credentials between agents before transacting.",
                examples: ["KYC verification", "Mandate validation", "Capability proofs", "Trust scoring"]
              }
            ].map((useCase, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="flex items-start gap-4">
                      <div className="w-14 h-14 border border-border flex items-center justify-center group-hover:border-[var(--sardis-orange)] transition-colors shrink-0">
                        <IsometricIcon src={useCase.icon} className="w-8 h-8" isDark={isDark} />
                      </div>
                      <div>
                        <CardTitle className="text-xl font-bold font-display mb-2">{useCase.title}</CardTitle>
                        <p className="text-muted-foreground text-sm leading-relaxed">
                          {useCase.description}
                        </p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {useCase.examples.map((example, j) => (
                        <Badge key={j} variant="outline" className="rounded-none text-xs font-mono border-border">
                          {example}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Ecosystem Contribution Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">OPEN SOURCE</Badge>
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">Contributing to the Ecosystem</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              We believe the agent economy needs open infrastructure. Our SDKs, tools, and reference implementations are free for everyone.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: icons.terminal,
                title: "Multi-Language SDKs",
                description: "Full-featured SDKs for Python and TypeScript. Create wallets, execute payments, manage policies - all with type-safe APIs.",
                links: [
                  { name: "Python SDK", url: "https://github.com/EfeDurmaz16/sardis" },
                  { name: "TypeScript SDK", url: "https://github.com/EfeDurmaz16/sardis" }
                ]
              },
              {
                icon: icons.autoRenew,
                title: "MCP Server",
                description: "Native integration with Claude, Cursor, and any MCP-compatible AI. 52 tools for payments, wallets, holds, invoices, and commerce.",
                links: [
                  { name: "npm package", url: "https://www.npmjs.com/package/@sardis/mcp-server" },
                  { name: "GitHub", url: "https://github.com/EfeDurmaz16/sardis" }
                ]
              },
              {
                icon: icons.searchInsights,
                title: "Reference Implementations",
                description: "Complete examples for common patterns: shopping agents, subscription management, multi-agent coordination, and more.",
                links: [
                  { name: "Examples", url: "https://github.com/EfeDurmaz16/sardis/tree/main/examples" },
                  { name: "Demos", url: "https://github.com/EfeDurmaz16/sardis/tree/main/demos" }
                ]
              }
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="w-16 h-16 border border-border flex items-center justify-center mb-4 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <IsometricIcon src={item.icon} className="w-10 h-10" isDark={isDark} />
                    </div>
                    <CardTitle className="text-xl font-bold font-display">{item.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-muted-foreground leading-relaxed">
                      {item.description}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {item.links.map((link, j) => (
                        <a
                          key={j}
                          href={link.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-mono text-[var(--sardis-orange)] hover:underline"
                        >
                          {link.name} →
                        </a>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Protocol packages highlight */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-12 p-8 border border-border"
          >
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold font-display mb-2">Protocol Packages</h3>
              <p className="text-muted-foreground">Standalone implementations of each protocol - use them independently or as part of Sardis.</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { name: "sardis-protocol", desc: "AP2/TAP verification" },
                { name: "sardis-ucp", desc: "Universal Commerce" },
                { name: "sardis-a2a", desc: "Agent-to-Agent" },
                { name: "sardis-chain", desc: "Multi-chain execution" }
              ].map((pkg, i) => (
                <div key={i} className="p-4 border border-border hover:border-[var(--sardis-orange)] transition-colors text-center">
                  <code className="text-sm font-mono text-[var(--sardis-orange)]">{pkg.name}</code>
                  <p className="text-xs text-muted-foreground mt-1">{pkg.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Install SDKs Section */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-12"
          >
            <div className="text-center mb-8">
              <Badge variant="outline" className="mb-4 text-yellow-600 dark:text-yellow-400 border-yellow-600/30 dark:border-yellow-400/30 rounded-none font-mono">EARLY ACCESS</Badge>
              <h3 className="text-2xl font-bold font-display mb-2">Install the SDKs</h3>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Our packages are live on npm and PyPI. The hosted API is launching soon — join the waitlist for early access and an API key.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Python SDKs */}
              <div className="border border-border p-6 space-y-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 border border-border flex items-center justify-center">
                    <span className="text-lg font-bold font-mono text-[var(--sardis-orange)]">Py</span>
                  </div>
                  <div>
                    <h4 className="font-bold font-display">Python Packages</h4>
                    <a href="https://pypi.org/user/sardis/" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-[var(--sardis-orange)] font-mono">pypi.org/user/sardis →</a>
                  </div>
                </div>
                <CopyCommand command="pip install sardis" />
                <CopyCommand command="pip install sardis-core" />
                <CopyCommand command="pip install sardis-protocol" />
                <div className="pt-3 border-t border-border">
                  <p className="text-xs text-muted-foreground font-mono mb-2">Also available:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {["sardis-api", "sardis-chain", "sardis-wallet", "sardis-ledger", "sardis-compliance", "sardis-cards", "sardis-cli", "sardis-checkout", "sardis-ramp", "sardis-ucp", "sardis-a2a"].map((pkg) => (
                      <a key={pkg} href={`https://pypi.org/project/${pkg}/`} target="_blank" rel="noopener noreferrer" className="text-xs font-mono px-2 py-0.5 border border-border hover:border-[var(--sardis-orange)] hover:text-[var(--sardis-orange)] transition-colors">
                        {pkg}
                      </a>
                    ))}
                  </div>
                </div>
              </div>

              {/* npm SDKs */}
              <div className="border border-border p-6 space-y-4">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 border border-border flex items-center justify-center">
                    <span className="text-lg font-bold font-mono text-[var(--sardis-orange)]">JS</span>
                  </div>
                  <div>
                    <h4 className="font-bold font-display">npm Packages</h4>
                    <a href="https://www.npmjs.com/org/sardis" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-[var(--sardis-orange)] font-mono">npmjs.com/org/sardis →</a>
                  </div>
                </div>
                <CopyCommand command="npm install @sardis/sdk" />
                <CopyCommand command="npm install @sardis/mcp-server" />
                <CopyCommand command="npm install @sardis/ai-sdk" />
                <div className="pt-3 border-t border-border">
                  <p className="text-xs text-muted-foreground font-mono mb-2">Also available:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {["@sardis/ramp"].map((pkg) => (
                      <a key={pkg} href={`https://www.npmjs.com/package/${pkg}`} target="_blank" rel="noopener noreferrer" className="text-xs font-mono px-2 py-0.5 border border-border hover:border-[var(--sardis-orange)] hover:text-[var(--sardis-orange)] transition-colors">
                        {pkg}
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Early access note */}
            <div className="mt-6 p-4 border border-yellow-600/30 dark:border-yellow-400/30 bg-yellow-500/5">
              <p className="text-sm text-center text-muted-foreground">
                <span className="font-bold text-yellow-600 dark:text-yellow-400">Note:</span> SDKs require a Sardis API key to connect to the hosted backend. The API is currently in private beta — <button onClick={() => setIsWaitlistOpen(true)} className="text-[var(--sardis-orange)] hover:underline font-medium">join the waitlist</button> to get early access.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Traction Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row items-end justify-between mb-12 gap-8">
            <div>
              <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">Traction & Trust</h2>
              <p className="text-lg text-muted-foreground max-w-xl">
                We are building the financial rails for the next generation of commerce.
              </p>
            </div>

            <a
              href="https://sepolia.basescan.org/address/0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7"
              target="_blank"
              rel="noreferrer"
              className="group flex items-center gap-3 px-5 py-3 border border-border hover:border-[var(--sardis-orange)] transition-colors"
            >
              <div className="w-8 h-8 border border-border group-hover:border-[var(--sardis-orange)] flex items-center justify-center">
                <IsometricIcon src={icons.searchInsights} className="w-5 h-5" isDark={isDark} />
              </div>
              <div className="text-sm text-left">
                <div className="text-xs text-muted-foreground uppercase tracking-wider font-mono font-semibold">Verify on BaseScan</div>
                <div className="font-mono text-foreground group-hover:text-[var(--sardis-orange)] transition-colors">0x0922...3D7</div>
              </div>
            </a>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              { label: "ADOPTION", value: "3,500+", sub: "package installs (npm + PyPI) • 19 packages" },
              { label: "MCP SERVER", value: "46 Tools", sub: "Live on npm • zero-config for Claude & Cursor" },
              { label: "INFRASTRUCTURE", value: "5 Chains • 5 Protocols", sub: "AP2 • TAP • UCP • A2A • x402" }
            ].map((stat, i) => (
              <div key={i} className="p-8 border border-border hover:border-[var(--sardis-orange)] transition-colors">
                <div className="text-xs font-bold tracking-widest text-[var(--sardis-orange)] mb-2 font-mono">{stat.label}</div>
                <div className="text-3xl font-bold text-foreground mb-1 font-display">{stat.value}</div>
                <div className="text-sm text-muted-foreground font-mono">{stat.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Founder Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="max-w-4xl mx-auto border border-border p-8 md:p-12 relative overflow-hidden">
            {/* Decorative quote mark */}
            <div className="absolute top-4 right-8 text-border font-serif text-9xl leading-none">"</div>

            <div className="flex flex-col md:flex-row gap-8 items-start relative z-10">
              <Avatar className="w-24 h-24 md:w-32 md:h-32 border-2 border-[var(--sardis-orange)] rounded-none">
                <AvatarImage src="/efe-avatar.png" />
                <AvatarFallback className="bg-[var(--sardis-orange)]/10 text-[var(--sardis-orange)] text-2xl font-bold rounded-none">ED</AvatarFallback>
              </Avatar>

              <div className="flex-1">
                <blockquote className="text-xl md:text-2xl font-medium leading-relaxed mb-6 text-foreground">
                  "I hit this wall myself while building AI agents for the past 18 months. I'm building Sardis to solve the execution gap I faced as an engineer."
                </blockquote>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-border pt-6">
                  <div>
                    <div className="font-bold text-lg text-foreground font-display">Efe Baran Durmaz</div>
                    <div className="text-[var(--sardis-orange)]">AI Architect & Engineer</div>
                  </div>

                  <div className="flex gap-3">
                    <Button variant="outline" size="sm" className="h-9 gap-2 rounded-none border-border hover:border-[var(--sardis-orange)]" asChild>
                      <a href="https://linkedin.com/in/efe-baran-durmaz" target="_blank" rel="noreferrer">
                        <span className="font-bold">in</span> LinkedIn
                      </a>
                    </Button>
                    <Button variant="outline" size="sm" className="h-9 gap-2 rounded-none border-border hover:border-[var(--sardis-orange)]" asChild>
                      <a href="mailto:efe@sardis.dev">
                        Mail
                      </a>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 text-center border-t border-border">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl md:text-5xl font-display font-bold mb-6">Start Building with Sardis</h2>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            Give your agents financial autonomy today. Get hands-on support and full access to the production-ready platform.
          </p>
          <WaitlistForm />
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-start gap-8 mb-8">
            <div className="flex items-center gap-3">
              <SardisLogo size="small" />
              <span className="font-bold font-display">Sardis</span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Product</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><a href="/docs" className="hover:text-[var(--sardis-orange)] transition-colors">Documentation</a></li>
                  <li><a href="/docs/quickstart" className="hover:text-[var(--sardis-orange)] transition-colors">Quick Start</a></li>
                  <li><a href="/docs/sdk" className="hover:text-[var(--sardis-orange)] transition-colors">SDKs</a></li>
                  <li><a href="/playground" className="hover:text-[var(--sardis-orange)] transition-colors">Playground</a></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Resources</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><a href="/docs/blog" className="hover:text-[var(--sardis-orange)] transition-colors">Blog</a></li>
                  <li><a href="/docs/changelog" className="hover:text-[var(--sardis-orange)] transition-colors">Changelog</a></li>
                  <li><a href="/docs/roadmap" className="hover:text-[var(--sardis-orange)] transition-colors">Roadmap</a></li>
                  <li><a href="/docs/security" className="hover:text-[var(--sardis-orange)] transition-colors">Security</a></li>
                  <li><a href="https://context7.com/efedurmaz16/sardis" target="_blank" rel="noreferrer" className="hover:text-[var(--sardis-orange)] transition-colors">Context7 (AI Docs)</a></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Legal</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><a href="/docs/terms" className="hover:text-[var(--sardis-orange)] transition-colors">Terms of Service</a></li>
                  <li><a href="/docs/privacy" className="hover:text-[var(--sardis-orange)] transition-colors">Privacy Policy</a></li>
                  <li><a href="/docs/acceptable-use" className="hover:text-[var(--sardis-orange)] transition-colors">Acceptable Use</a></li>
                  <li><a href="/docs/risk-disclosures" className="hover:text-[var(--sardis-orange)] transition-colors">Risk Disclosures</a></li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-3 text-foreground">Connect</h4>
                <ul className="space-y-2 text-muted-foreground">
                  <li><a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noreferrer" className="hover:text-[var(--sardis-orange)] transition-colors">GitHub</a></li>
                  <li><a href="https://x.com/sardisHQ" target="_blank" rel="noreferrer" className="hover:text-[var(--sardis-orange)] transition-colors">X (Twitter)</a></li>
                  <li><a href="https://discord.gg/XMA9JwDJ" target="_blank" rel="noreferrer" className="hover:text-[var(--sardis-orange)] transition-colors">Discord</a></li>
                  <li><a href="mailto:contact@sardis.sh" className="hover:text-[var(--sardis-orange)] transition-colors">Contact</a></li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex flex-col md:flex-row justify-between items-center gap-4 pt-8 border-t border-border">
            <div className="flex gap-6 text-xs text-muted-foreground font-mono">
              <span>Non-Custodial</span>
              <span>Multi-Chain</span>
              <span>AP2 Compliant</span>
            </div>

            <div className="text-xs text-muted-foreground font-mono">
              © 2026 Sardis. All rights reserved.
            </div>
          </div>
        </div>
      </footer>

      {/* Waitlist Modal */}
      <WaitlistModal isOpen={isWaitlistOpen} onClose={() => setIsWaitlistOpen(false)} />
    </div>
  );
}

export default App;
