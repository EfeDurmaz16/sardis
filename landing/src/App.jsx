import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Sun, Moon, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import SardisPlayground from "./components/SardisPlayground";
import WaitlistForm from "./components/WaitlistForm";
import SardisLogo from "./components/SardisLogo";
import WaitlistModal from "./components/WaitlistModal";
import SEO, { createOrganizationSchema, createSoftwareAppSchema, createWebSiteSchema } from "@/components/SEO";

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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

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
      <SEO
        title="Sardis AI Agent Payments"
        description="Sardis lets AI agents make real payments safely. Policy-controlled wallets for cards, crypto, and fiat. The agent never touches private keys."
        path="/"
        schemas={[
          createOrganizationSchema(),
          createWebSiteSchema(),
          createSoftwareAppSchema(),
        ]}
      />

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
              className="ml-2 bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20"
              onClick={() => setIsWaitlistOpen(true)}
            >
              Get Early Access
            </Button>
          </div>

          {/* Mobile hamburger */}
          <div className="flex md:hidden items-center gap-2">
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="w-10 h-10 border border-border hover:border-[var(--sardis-orange)] transition-colors flex items-center justify-center"
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? (
                <X className="w-5 h-5 text-foreground" />
              ) : (
                <Menu className="w-5 h-5 text-foreground" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile menu dropdown */}
        {isMobileMenuOpen && (
          <div className="md:hidden border-t border-border bg-background/95 backdrop-blur-sm">
            <div className="container mx-auto px-6 py-4 flex flex-col gap-3">
              <Link to="/docs" className="text-muted-foreground hover:text-foreground py-2" onClick={() => setIsMobileMenuOpen(false)}>Docs</Link>
              <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground py-2" onClick={() => setIsMobileMenuOpen(false)}>GitHub</a>
              <Button
                className="bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20 w-full"
                onClick={() => { setIsWaitlistOpen(true); setIsMobileMenuOpen(false); }}
              >
                Get Early Access
              </Button>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative pt-28 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        {/* Atmospheric background */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 -right-32 w-96 h-96 bg-[var(--sardis-orange)]/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 -left-32 w-80 h-80 bg-[var(--sardis-teal)]/5 rounded-full blur-3xl" />
        </div>

        <div className="container mx-auto px-6 relative z-10">
          <div className="max-w-5xl mx-auto text-center">
            <p className="mb-5 inline-flex items-center border border-border bg-background/70 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Safe Payments for AI Agents
            </p>

            <h1 className="mx-auto max-w-[18ch] text-[clamp(2.45rem,7.4vw,5.8rem)] font-sans font-semibold leading-[1.04] tracking-[-0.028em] mb-6">
              <span className="block">AI agents can reason.</span>
              <span className="block">Now they can pay.</span>
            </h1>

            <p className="text-[1.05rem] md:text-[1.35rem] text-muted-foreground mb-6 max-w-2xl mx-auto leading-relaxed">
              Your agents hit a wall at checkout. 2FA, CAPTCHAs, OTPs. Sardis removes that wall with policy-controlled wallets and secure payment rails.
            </p>

            <p className="text-sm md:text-base text-muted-foreground mb-8 max-w-[58ch] mx-auto">
              Define spending rules in plain English. Sardis enforces them before any money moves.
            </p>

            <div className="mb-8 flex flex-wrap items-center justify-center gap-2 text-xs font-mono">
              <span className="border border-border bg-background/70 px-2.5 py-1 text-muted-foreground">
                You set the rules
              </span>
              <span className="border border-border bg-background/70 px-2.5 py-1 text-muted-foreground">
                Cards + Crypto + Bank
              </span>
              <span className="border border-border bg-background/70 px-2.5 py-1 text-muted-foreground">
                Works with any AI agent
              </span>
            </div>

            <div className="max-w-3xl mx-auto">
              <CopyCommand command="npx @sardis/mcp-server init --mode simulated && npx @sardis/mcp-server start" />
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-10 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { number: "0", label: "Private Keys Stored" },
              { number: "<1s", label: "Policy Check to Settlement" },
              { number: "5", label: "Chains Supported" },
              { number: "52", label: "MCP Tools" },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-3xl font-display font-bold text-[var(--sardis-orange)]">{stat.number}</div>
                <div className="text-sm text-muted-foreground mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Separator */}
      <div className="relative h-px w-full">
        <div className="absolute inset-0 bg-border" />
        <div className="absolute left-1/2 -translate-x-1/2 -top-3 bg-background px-4">
          <div className="w-4 h-4 bg-[var(--sardis-orange)] rotate-45" />
        </div>
      </div>

      {/* API-First Code Snippet */}
      <section className="py-24 md:py-32">
        <div className="container mx-auto px-6">
          <div className="max-w-3xl mx-auto">
            <div className="text-center mb-10">
              <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">5 Lines of Code</p>
              <h3 className="text-3xl md:text-4xl font-semibold font-display">Give your agent a wallet. Set the rules. Done.</h3>
            </div>
            <div className="border border-border bg-card overflow-hidden">
              <div className="bg-muted px-4 py-3 border-b border-border flex items-center justify-between">
                <div className="flex gap-2">
                  <div className="w-3 h-3 bg-destructive" />
                  <div className="w-3 h-3 bg-yellow-500" />
                  <div className="w-3 h-3 bg-emerald-500" />
                </div>
                <span className="text-xs font-mono text-muted-foreground">python | pip install sardis</span>
              </div>
              <div className="p-6 font-mono text-sm bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] text-[var(--sardis-canvas)] overflow-x-auto">
                <table className="border-collapse w-full">
                  <tbody>
                    {[
                      { n: 1, code: <><span className="text-[#c678dd]">from</span> sardis <span className="text-[#c678dd]">import</span> SardisClient</> },
                      { n: 2, code: <>client = SardisClient()</> },
                      { n: 3, code: <>&nbsp;</> },
                      { n: 4, code: <>wallet = client.wallets.create(</> },
                      { n: 5, code: <>&nbsp;&nbsp;&nbsp;&nbsp;policy=<span className="text-[#98c379]">"Max $100/day, only SaaS vendors"</span></> },
                      { n: 6, code: <>)</> },
                      { n: 7, code: <>wallet.pay(<span className="text-[#98c379]">"openai"</span>, <span className="text-[#d19a66]">45.00</span>, purpose=<span className="text-[#98c379]">"API credits"</span>)</> },
                      { n: 8, code: <span className="text-emerald-400"># Policy check → MPC signing → settlement. That's it.</span> },
                    ].map((line) => (
                      <tr key={line.n} className="leading-7">
                        <td className="w-8 text-right pr-4 select-none text-[var(--sardis-canvas)]/25 align-top">{line.n}</td>
                        <td className="whitespace-pre">{line.code}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section: What Happens Without Guardrails */}
      <section className="py-28 md:py-36 relative border-t border-border">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-20 items-center">
            <div>
              <p className="text-lg font-mono text-destructive tracking-[0.08em] font-bold mb-4 uppercase">THE PROBLEM</p>
              <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6 leading-tight">What Happens Without Guardrails</h2>
              <p className="text-lg text-muted-foreground mb-6 leading-relaxed">
                AI agents can reason, plan, and execute complex workflows. But they <strong className="text-foreground font-medium">fail at checkout</strong>.
              </p>
              <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                Payment rails were built to block non-human actors. 2FA, OTPs, CAPTCHAs. That was the right design, until agents needed to pay.
              </p>

              <ul className="space-y-4">
                {[
                  { text: "An agent stuck in a retry loop made 47,000 API calls in 6 hours. $1,410 burned.", icon: icons.autoRenew },
                  { text: "A McDonald's AI kept adding McNuggets to an order. 260 pieces before anyone noticed.", icon: icons.trendingUp },
                  { text: "73% of teams have no real-time cost tracking for autonomous agents.", icon: icons.policy },
                  { text: "Agent cost overruns average 340% above initial estimates.", icon: icons.searchInsights }
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-lg text-destructive">
                    <div className="w-10 h-10 border border-destructive/30 flex items-center justify-center">
                      <IsometricIcon src={item.icon} className="w-6 h-6" isDark={isDark} />
                    </div>
                    {item.text}
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative">
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
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Demo */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-10">
            <p className="text-sm font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">Live Demo</p>
            <h3 className="text-3xl md:text-4xl font-bold font-display">Try It Now</h3>
          </div>
          <div className="max-w-5xl mx-auto">
            <SardisPlayground />
          </div>
        </div>
      </section>

      {/* Features Section: Built for Agent Payments */}
      <section className="py-28 md:py-36 border-t border-border relative">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/2 -right-48 w-[500px] h-[500px] bg-[var(--sardis-orange)]/3 rounded-full blur-[120px]" />
        </div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="text-center mb-20">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">What We Enable</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-5">Your Agent's Missing Financial Layer</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Agents can book flights, pay invoices, and manage subscriptions. No human approval needed. No private keys exposed.
            </p>
          </div>

          {/* Bento grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                icon: icons.autoRenew,
                title: "No More 2FA Walls",
                description: "Agents get stuck at checkout because payment rails were built to block non-humans. Sardis gives them a secure path through.",
                span: false,
              },
              {
                icon: icons.policy,
                title: "Spending Rules in Plain English",
                description: "\"Max $200/day, only SaaS vendors, no weekend transactions.\" Write policies like you'd brief a junior employee. Sardis enforces them deterministically.",
                span: false,
              },
              {
                icon: icons.creditCardGear,
                title: "Cards, Crypto, and Bank Transfers",
                description: "One API for every payment rail. Virtual Visa cards for web purchases, stablecoin for on-chain, and fiat for traditional vendors.",
                span: false,
              },
              {
                icon: icons.shieldLock,
                title: "You Stay in Control",
                description: "Sardis never holds your funds or keys. Wallets are secured by distributed key management. No single entity, not even Sardis, can move your money.",
                span: false,
              },
              {
                icon: icons.searchInsights,
                title: "Every Transaction Auditable",
                description: "Append-only ledger with cryptographic proofs anchored on-chain. Know exactly what every agent spent, when, and why.",
                span: false,
              },
              {
                icon: icons.wallet,
                title: "Kill Switch Built In",
                description: "Pause any agent wallet instantly. Rate limiters and behavioral monitoring detect anomalies and halt spending before damage is done.",
                span: false,
              },
            ].map((feature, i) => (
              <div
                key={i}
                className={feature.span ? "md:col-span-2 lg:col-span-2" : ""}
              >
                <Card className={cn(
                  "h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group",
                  feature.span && "flex flex-col md:flex-row md:items-center"
                )}>
                  <CardHeader className={feature.span ? "md:w-1/2" : ""}>
                    <div className="w-14 h-14 border border-border flex items-center justify-center mb-4 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <IsometricIcon src={feature.icon} className="w-9 h-9" isDark={isDark} />
                    </div>
                    <CardTitle className="text-lg font-semibold font-display">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent className={feature.span ? "md:w-1/2" : ""}>
                    <p className="text-muted-foreground leading-relaxed">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Sardis Section - Competitive Positioning */}
      <section className="py-28 md:py-36 border-t border-border relative">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute bottom-0 -left-32 w-[400px] h-[400px] bg-[var(--sardis-teal)]/5 rounded-full blur-[100px]" />
        </div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="text-center mb-20">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">Why Sardis</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-5">Trust Without Giving Up Control</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-6 mb-12">
            {[
              {
                icon: icons.policy,
                title: "Natural Language Policies",
                description: "Define complex spending rules in plain English. 7 built-in templates, preview before deploy, context-aware governance.",
                unique: true
              },
              {
                icon: icons.shieldLock,
                title: "Non-Custodial Security",
                description: "Your keys, your funds. Secured by distributed key management so no single entity can move money without your approval.",
                unique: false
              },
              {
                icon: icons.terminal,
                title: "Zero-Config MCP",
                description: "One command to add 52 payment and treasury tools to Claude or Cursor. No setup required.",
                unique: false
              },
              {
                icon: icons.searchInsights,
                title: "Confidence Routing",
                description: "Tiered approval workflows based on transaction confidence scores. Supports 4-eyes quorum with distinct reviewers for high-risk control mutations.",
                unique: true
              },
              {
                icon: icons.autoRenew,
                title: "Goal Drift Guard",
                description: "Chi-squared behavioral analysis detects when agents deviate from expected spending patterns. Automatic velocity governors.",
                unique: true
              },
              {
                icon: icons.wallet,
                title: "Merkle Audit Trail",
                description: "Tamper-proof audit logs anchored to Base blockchain via Merkle trees. Cryptographic proof for transactions and trust-policy mutations.",
                unique: true
              }
            ].map((item, i) => (
              <div
                key={i}
                className="w-full md:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)]"
              >
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group relative">
                  {item.unique && (
                    <div className="absolute top-3 right-3">
                      <Badge className="bg-[#9DD9D2] text-[#1a1614] rounded-none text-xs font-mono">
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
              </div>
            ))}
          </div>

          {/* Replacement for competitor callout */}
          <div className="p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
            <p className="text-muted-foreground">The only platform combining natural language policies, per-transaction risk scoring, drift detection, and cryptographic audit. All without holding your private keys.</p>
          </div>
        </div>
      </section>

      {/* Protocol Ecosystem Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-teal-strong)] dark:text-[#9DD9D2] border-[var(--sardis-teal-strong)]/30 dark:border-[#9DD9D2]/30 rounded-none font-mono">PROTOCOL NATIVE</Badge>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Built on Open Standards</h2>
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
                fullName: "Trusted Agent Protocol",
                description: "Cryptographic identity verification. Agent attestation and credential chains.",
                status: "Implemented"
              }
            ].map((protocol, i) => (
              <div key={i}>
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
                    <CardTitle className="text-lg font-semibold font-display text-[var(--sardis-orange)]">{protocol.name}</CardTitle>
                    <p className="text-sm text-muted-foreground font-mono">{protocol.fullName}</p>
                  </CardHeader>
                  <CardContent>
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {protocol.description}
                    </p>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>

          {/* x402 Micropayments highlight */}
          <div className="mt-8 p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors">
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="w-16 h-16 border border-border flex items-center justify-center">
                <IsometricIcon src={icons.creditCardGear} className="w-10 h-10" isDark={isDark} />
              </div>
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-base font-semibold font-display mb-1">x402 Micropayments</h3>
                <p className="text-muted-foreground">HTTP 402 Payment Required - Pay-per-API-call for agent services. Sub-cent transactions with instant settlement.</p>
              </div>
              <Badge variant="outline" className="text-emerald-600 border-emerald-600/30 rounded-none font-mono">
                Implemented
              </Badge>
            </div>
          </div>
        </div>
      </section>

      {/* AI Framework Integrations Section */}
      <section className="py-28 md:py-36 border-t border-border relative">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/3 -left-48 w-[500px] h-[500px] bg-[var(--sardis-orange)]/3 rounded-full blur-[120px]" />
        </div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">WORKS EVERYWHERE</Badge>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-5">One Payment Layer. Every AI Platform.</h2>
            <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
              Add financial capabilities to any AI agent, regardless of framework or model. Sardis speaks every protocol.
            </p>
          </div>

          {/* OpenClaw Hero Card */}
          <div className="mb-8 p-8 border-2 border-[var(--sardis-orange)] bg-[var(--sardis-orange)]/5 relative overflow-hidden">
            <div className="absolute top-3 right-3">
              <Badge className="bg-[var(--sardis-orange)] text-white rounded-none text-xs font-mono animate-pulse">
                TRENDING
              </Badge>
            </div>
            <div className="flex flex-col md:flex-row items-start gap-8">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-14 h-14 border-2 border-[var(--sardis-orange)] flex items-center justify-center bg-[var(--sardis-orange)]/10">
                    <img src="/icons/openclaw.svg" alt="OpenClaw" className="w-8 h-8" style={{ filter: isDark ? 'invert(1)' : 'none' }} />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold font-display">OpenClaw Skill</h3>
                    <p className="text-sm text-muted-foreground font-mono">sardis-openclaw</p>
                  </div>
                </div>
                <p className="text-lg text-muted-foreground leading-relaxed mb-4">
                  Sardis is available as an <strong className="text-foreground">OpenClaw skill</strong>, the fastest way to give any agent financial powers.
                  Install once, and every OpenClaw-compatible agent instantly gets access to payments, virtual cards, balance checks, and policy management.
                </p>
                <div className="flex flex-wrap gap-2 mb-6">
                  {["send_payment", "check_balance", "create_card", "set_policy", "get_transactions", "fund_wallet"].map((tool) => (
                    <span key={tool} className="px-2 py-1 text-xs font-mono border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/10 text-[var(--sardis-orange)]">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
              <div className="w-full md:w-auto md:min-w-[320px]">
                <div className="border border-border bg-card overflow-hidden">
                  <div className="bg-muted px-4 py-2.5 border-b border-border flex items-center gap-2">
                    <div className="w-2.5 h-2.5 bg-destructive" />
                    <div className="w-2.5 h-2.5 bg-yellow-500" />
                    <div className="w-2.5 h-2.5 bg-emerald-500" />
                    <span className="ml-3 text-xs font-mono text-muted-foreground">SKILL.md</span>
                  </div>
                  <div className="p-4 font-mono text-xs leading-relaxed bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] text-[var(--sardis-canvas)]">
                    <div><span className="text-[#c678dd]">name:</span> sardis-pay</div>
                    <div><span className="text-[#c678dd]">version:</span> 0.9.0</div>
                    <div><span className="text-[#c678dd]">description:</span> <span className="text-[#98c379]">Payment OS for agents</span></div>
                    <div className="mt-2"><span className="text-[#c678dd]">tools:</span></div>
                    <div>&nbsp;&nbsp;- <span className="text-[#98c379]">send_payment</span></div>
                    <div>&nbsp;&nbsp;- <span className="text-[#98c379]">check_balance</span></div>
                    <div>&nbsp;&nbsp;- <span className="text-[#98c379]">create_virtual_card</span></div>
                    <div>&nbsp;&nbsp;- <span className="text-[#98c379]">set_spending_policy</span></div>
                    <div className="mt-2 text-emerald-400"># Works with any OpenClaw agent</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Other Frameworks Grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                logo: "/icons/mcp.svg",
                name: "Claude / MCP",
                description: "52 MCP tools. One command to add payments to Claude Desktop, Cursor, or any MCP client.",
                code: "npx @sardis/mcp-server start",
                badge: "52 tools"
              },
              {
                logo: "/icons/openai-2.svg",
                name: "OpenAI / GPT",
                description: "Strict-mode function calling tools. Drop-in for GPT-4, GPT-4o, and Assistants API.",
                code: "pip install sardis-openai",
                badge: "Strict JSON"
              },
              {
                logo: "/icons/gemini.svg",
                name: "Google Gemini / ADK",
                description: "Native FunctionDeclaration adapters for Gemini Pro, Ultra, and Agent Development Kit.",
                code: "pip install sardis-adk",
                badge: "ADK native"
              },
              {
                logo: "/icons/openai-2.svg",
                name: "ChatGPT Actions",
                description: "OpenAPI 3.0 spec with 8 endpoints. Any custom GPT can query balances, send payments, and manage cards.",
                code: "/openapi-actions.yaml",
                badge: "No code"
              },
              {
                logo: "/icons/langchain.svg",
                name: "LangChain / CrewAI",
                description: "Native tool integrations for LangChain agents, CrewAI crews, and LlamaIndex workflows.",
                code: "pip install sardis-langchain",
                badge: "Python + JS"
              },
              {
                logo: "/icons/vercel.svg",
                name: "Vercel AI SDK",
                description: "TypeScript-first integration with proper mandate signing for Next.js and Edge deployments.",
                code: "npm install @sardis/ai-sdk",
                badge: "TypeScript"
              },
            ].map((framework, i) => (
              <div key={i}>
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between mb-3">
                      <div className="w-10 h-10 border border-border flex items-center justify-center group-hover:border-[var(--sardis-orange)] transition-colors">
                        <img src={framework.logo} alt={framework.name} className="w-6 h-6" style={{ filter: isDark ? 'invert(1)' : 'none' }} />
                      </div>
                      <Badge variant="outline" className="text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none text-xs font-mono">
                        {framework.badge}
                      </Badge>
                    </div>
                    <CardTitle className="text-base font-bold font-display">{framework.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {framework.description}
                    </p>
                    <code className="block text-xs font-mono px-3 py-2 bg-muted border border-border text-[var(--sardis-orange)] truncate">
                      {framework.code}
                    </code>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>

          {/* Bottom CTA */}
          <div className="mt-8 p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 text-center">
            <p className="text-lg font-medium mb-2">
              Your framework not listed? Sardis has a REST API. If it speaks HTTP, it works.
            </p>
            <p className="text-sm text-muted-foreground">
              <Link to="/docs/api-reference" className="text-[var(--sardis-orange)] hover:underline">View API Reference →</Link>
            </p>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-28 md:py-36 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <p className="text-lg font-mono text-[var(--sardis-teal-strong)] dark:text-[#9DD9D2] tracking-[0.08em] font-bold mb-4 uppercase">How It Works</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Four Steps. Zero Complexity.</h2>
            <p className="text-base text-muted-foreground max-w-lg mx-auto">
              Your agent says "pay." Sardis handles everything between intent and settlement.
            </p>
          </div>

          {/* Timeline-style steps with connecting line */}
          <div className="relative">
            {/* Connecting line (desktop) */}
            <div className="hidden lg:block absolute top-10 left-[calc(12.5%+1rem)] right-[calc(12.5%+1rem)] h-px bg-border z-0" />

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
              {[
                {
                  step: "01",
                  title: "Agent Creates Intent",
                  desc: "Your agent says 'Pay OpenAI $45 for API credits.' Sardis takes it from there."
                },
                {
                  step: "02",
                  title: "Policy Validation",
                  desc: "Spending limits, merchant rules, time windows. All checked before any money moves."
                },
                {
                  step: "03",
                  title: "Secure Signing",
                  desc: "Secure custody ensures no single entity can move funds. The agent never touches private keys."
                },
                {
                  step: "04",
                  title: "Settlement",
                  desc: "Payment executes via the optimal rail. Virtual card, bank transfer, or direct settlement."
                }
              ].map((item, i) => (
                <div
                  key={i}
                  className="relative"
                >
                  {/* Step number circle */}
                  <div className="w-10 h-10 border-2 border-[var(--sardis-orange)] bg-background flex items-center justify-center mb-5 font-mono font-bold text-sm text-[var(--sardis-orange)]">
                    {item.step}
                  </div>
                  <h4 className="font-semibold font-display mb-2">{item.title}</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-12 max-w-2xl mx-auto">
            <div className="border border-[var(--sardis-orange)]/20 bg-[var(--sardis-orange)]/5 p-6 text-center">
              <p className="text-sm font-mono text-[var(--sardis-orange)] tracking-[0.12em] font-bold uppercase mb-2">End to End</p>
              <p className="text-lg text-muted-foreground">
                Intent → Policy Check → Secure Signing → Settlement
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Every step is audited. Every transaction is traceable. No black boxes.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-rose-strong)] dark:text-[#f4d0df] border-[var(--sardis-rose-strong)]/30 dark:border-[#f4d0df]/30 rounded-none font-mono">WHO IS THIS FOR</Badge>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">If Your Agent Needs to Spend Money</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Whether you're building a shopping assistant, an ops automation, or a multi-agent team. If it needs to pay, Sardis makes it safe.
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
                description: "Coordinate payments across agent teams. One agent discovers, another negotiates, a third executes payment. Full audit trail at every step.",
                examples: ["Supply chain automation", "Research orchestration", "Content pipelines", "Trading systems"]
              },
              {
                icon: icons.verifiedUser,
                title: "Credential Verification",
                description: "Verify payment mandates, identity attestations, and capability credentials between agents before transacting.",
                examples: ["KYC verification", "Mandate validation", "Capability proofs", "Trust scoring"]
              }
            ].map((useCase, i) => (
              <div key={i}>
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="flex items-start gap-4">
                      <div className="w-14 h-14 border border-border flex items-center justify-center group-hover:border-[var(--sardis-orange)] transition-colors shrink-0">
                        <IsometricIcon src={useCase.icon} className="w-8 h-8" isDark={isDark} />
                      </div>
                      <div>
                        <CardTitle className="text-lg font-semibold font-display mb-2">{useCase.title}</CardTitle>
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
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Ecosystem Contribution Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-orange)] border-[var(--sardis-orange)]/30 rounded-none font-mono">OPEN SOURCE</Badge>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Start Building in Minutes</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Open-source SDKs, MCP tools, and examples. No vendor lock-in. Integrate with your stack and ship.
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
                description: "Native integration with Claude, Cursor, and any MCP-compatible AI. 52 tools for payments, wallets, treasury, fiat operations, holds, invoices, commerce, and guardrails.",
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
              <div key={i}>
                <Card className="h-full bg-card border-border hover:border-[var(--sardis-orange)] transition-all duration-200 rounded-none group">
                  <CardHeader>
                    <div className="w-16 h-16 border border-border flex items-center justify-center mb-4 group-hover:border-[var(--sardis-orange)] transition-colors">
                      <IsometricIcon src={item.icon} className="w-10 h-10" isDark={isDark} />
                    </div>
                    <CardTitle className="text-lg font-semibold font-display">{item.title}</CardTitle>
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
              </div>
            ))}
          </div>

          {/* Protocol packages highlight */}
          <div className="mt-12 p-8 border border-border">
            <div className="text-center mb-8">
              <h3 className="text-lg font-semibold font-display mb-2">Protocol Packages</h3>
              <p className="text-muted-foreground">Standalone implementations of each protocol - use them independently or as part of Sardis.</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { name: "sardis-protocol", desc: "AP2/TAP verification" },
                { name: "sardis-ucp", desc: "Universal Commerce" },
                { name: "sardis-a2a", desc: "Agent-to-Agent" },
                { name: "sardis-chain", desc: "Payment execution" }
              ].map((pkg, i) => (
                <div key={i} className="p-4 border border-border hover:border-[var(--sardis-orange)] transition-colors text-center">
                  <code className="text-sm font-mono text-[var(--sardis-orange)]">{pkg.name}</code>
                  <p className="text-xs text-muted-foreground mt-1">{pkg.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Traction Section */}
      <section className="py-24 border-t border-border">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row items-end justify-between mb-12 gap-8">
            <div>
              <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Already in Use</h2>
              <p className="text-lg text-muted-foreground max-w-xl">
                Developers are building with Sardis today. We're looking for design partners to shape what comes next.
              </p>
            </div>

            <a
              href="https://github.com/EfeDurmaz16/sardis"
              target="_blank"
              rel="noreferrer"
              className="group flex items-center gap-3 px-5 py-3 border border-border hover:border-[var(--sardis-orange)] transition-colors"
            >
              <div className="w-8 h-8 border border-border group-hover:border-[var(--sardis-orange)] flex items-center justify-center">
                <IsometricIcon src={icons.searchInsights} className="w-5 h-5" isDark={isDark} />
              </div>
              <div className="text-sm text-left">
                <div className="text-xs text-muted-foreground uppercase tracking-wider font-mono font-semibold">View on GitHub</div>
                <div className="font-mono text-foreground group-hover:text-[var(--sardis-orange)] transition-colors">Open Source</div>
              </div>
            </a>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              { label: "MARKET", value: "$30T by 2030", sub: <span>Machine Customer Economy, <a href="https://www.forbes.com/sites/torconstantino/2025/02/18/machine-customers-ai-buyers-to-control-30-trillion-in-purchases-by-2030/" target="_blank" rel="noreferrer" className="underline hover:text-[var(--sardis-orange)]">Gartner via Forbes</a></span> },
              { label: "ADOPTION", value: "25,000+", sub: <span>total installs across <span className="text-foreground">4 npm</span> + <span className="text-foreground">19 PyPI</span> packages</span> },
              { label: "STATUS", value: "Developer Preview", sub: "Private beta • accepting design partners" }
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
          <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6">Give Your Agents Financial Autonomy</h2>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            Join teams already building with Sardis. Get early access, hands-on onboarding, and help shape the payment OS for the agent economy.
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
              <span>You Own the Keys</span>
              <span>Policy-First</span>
              <span>Open Source</span>
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
