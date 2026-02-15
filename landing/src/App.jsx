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
              DEVELOPER PREVIEW • LOOKING FOR DESIGN PARTNERS
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
              className="ml-2 bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-semibold rounded-none shadow-md shadow-[var(--sardis-orange)]/20"
              onClick={() => setIsWaitlistOpen(true)}
            >
              Become a Design Partner
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-28 pb-20 md:pt-40 md:pb-32 overflow-hidden">
        {/* Atmospheric background */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 -right-32 w-96 h-96 bg-[var(--sardis-orange)]/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 -left-32 w-80 h-80 bg-[var(--sardis-teal)]/5 rounded-full blur-3xl" />
        </div>

        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial="initial"
            animate="animate"
            variants={staggerContainer}
            className="grid md:grid-cols-[1fr_auto] gap-16 items-center"
          >
            {/* Left: Text content */}
            <div>
              <motion.div variants={fadeInUp} className="mb-5">
                <Badge variant="outline" className="border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)] rounded-none font-mono text-xs tracking-widest">
                  DEVELOPER PREVIEW
                </Badge>
              </motion.div>

              <motion.h1 variants={fadeInUp} className="text-5xl md:text-6xl lg:text-7xl font-display font-bold leading-[1.05] tracking-tight mb-6">
                The Payment OS for the{" "}
                <span className="text-[var(--sardis-orange)]">Agent Economy</span>
              </motion.h1>

              <motion.p variants={fadeInUp} className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl leading-relaxed">
                Give your agents programmable wallets with natural language spending limits. Prevent financial hallucinations before they happen.
              </motion.p>

              <motion.div variants={fadeInUp}>
                <CopyCommand command="npx @sardis/mcp-server init --mode simulated && npx @sardis/mcp-server start" />
              </motion.div>
            </div>

            {/* Right: Metrics stack */}
            <motion.div
              variants={fadeInUp}
              className="hidden md:flex flex-col gap-4 w-64"
            >
              {[
                { label: "PACKAGES", value: "19", sub: "npm + PyPI" },
                { label: "MCP TOOLS", value: "50+", sub: "payment, treasury, cards" },
                { label: "PROTOCOLS", value: "4", sub: "AP2, UCP, A2A, TAP" },
              ].map((stat, i) => (
                <div
                  key={i}
                  className="p-5 border border-border hover:border-[var(--sardis-orange)] transition-colors group"
                >
                  <div className="text-[10px] font-bold tracking-[0.2em] text-muted-foreground mb-1 font-mono">{stat.label}</div>
                  <div className="text-2xl font-bold text-foreground font-display group-hover:text-[var(--sardis-orange)] transition-colors">{stat.value}</div>
                  <div className="text-xs text-muted-foreground font-mono">{stat.sub}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Separator — decorative */}
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
                <span className="text-xs font-mono text-muted-foreground">python — pip install sardis</span>
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

      {/* Problem Section: The Read-Only Trap */}
      <section className="py-28 md:py-36 relative border-t border-border">
        <div className="container mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-20 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <p className="text-lg font-mono text-destructive tracking-[0.08em] font-bold mb-4 uppercase">The Problem</p>
              <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6 leading-tight">The "Read-Only" Trap</h2>
              <p className="text-lg text-muted-foreground mb-6 leading-relaxed">
                AI agents can reason, plan, and execute complex workflows — but they <strong className="text-foreground font-medium">fail at checkout</strong>.
              </p>
              <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                Current payment rails (2FA, OTPs, CAPTCHAs) were built to block non-human actors. That was the right design — until now.
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
            className="mt-32 md:mt-40 max-w-5xl mx-auto"
          >
            <div className="text-center mb-10">
              <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">Interactive Demo</p>
              <h3 className="text-3xl md:text-4xl font-bold font-display">Experience the Spending Firewall</h3>
            </div>
            <SardisPlayground />
          </motion.div>
        </div>
      </section>

      {/* Features Section: Banking for Bots */}
      <section className="py-28 md:py-36 border-t border-border relative">
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/2 -right-48 w-[500px] h-[500px] bg-[var(--sardis-orange)]/3 rounded-full blur-[120px]" />
        </div>
        <div className="container mx-auto px-6 relative z-10">
          <div className="text-center mb-20">
            <p className="text-lg font-mono text-[var(--sardis-orange)] tracking-[0.08em] font-bold mb-4 uppercase">What You Get</p>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-5">Banking for Bots</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Programmable wallets, virtual cards, and spending controls purpose-built for AI agents.
            </p>
          </div>

          {/* Bento grid — hero card spans 2 cols */}
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                icon: icons.autoRenew,
                title: "Autonomous Execution",
                description: "Bypass human-centric 2FA barriers with secure autonomous signing. Agents can finally pay.",
                span: false,
              },
              {
                icon: icons.trendingUp,
                title: "Instant Settlement",
                description: "Policy-routed settlement across stablecoin, card, and fiat rails with provider-dependent settlement times.",
                span: false,
              },
              {
                icon: icons.creditCardGear,
                title: "Virtual Cards",
                description: "Instant Visa cards via Lithic. Your agent can pay anywhere cards are accepted — online and physical POS.",
                span: false,
              },
              {
                icon: icons.handshake,
                title: "Multi-Agent Groups",
                description: "Shared budgets across agent teams. Each agent gets individual limits, the group enforces the total. No agent overspends the team.",
                span: true,
              },
              {
                icon: icons.autoRenew,
                title: "Recurring Payments",
                description: "Subscription-aware billing engine. Register merchant + amount + cycle — Sardis auto-funds, auto-approves, and notifies the owner at every stage.",
                span: false,
              },
            ].map((feature, i) => (
              <motion.div
                key={i}
                className={feature.span ? "md:col-span-2 lg:col-span-2" : ""}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
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
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Fiat Rails Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container mx-auto px-6">
          <div className="text-center mb-16">
            <Badge variant="outline" className="mb-4 text-[var(--sardis-teal-strong)] dark:text-[#9DD9D2] border-[var(--sardis-teal-strong)]/30 dark:border-[#9DD9D2]/30 rounded-none font-mono">FIAT RAILS</Badge>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Unified Payment Rails</h2>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
              Fund agent wallets from your bank account. Pay via virtual card or direct transfer. Withdraw back to USD. One API, every rail.
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

              {/* Treasury */}
              <div className="flex flex-col items-center gap-2">
                <div className="w-16 h-16 border border-border flex items-center justify-center bg-muted">
                  <IsometricIcon src={icons.autoRenew} className="w-10 h-10" isDark={isDark} />
                </div>
                <span className="text-sm font-mono font-bold">Treasury</span>
                <span className="text-xs text-muted-foreground">USD first</span>
              </div>

              {/* Arrow */}
              <div className="flex flex-col items-center gap-1">
                <div className="h-0.5 w-12 bg-[var(--sardis-orange)]" />
                <span className="text-xs text-muted-foreground font-mono">Route</span>
              </div>

              {/* Sardis Wallet */}
              <div className="flex flex-col items-center gap-2">
                <div className="w-20 h-20 border-2 border-[var(--sardis-orange)] flex items-center justify-center bg-[var(--sardis-orange)]/10">
                  <IsometricIcon src={icons.wallet} className="w-12 h-12" isDark={isDark} />
                </div>
                <span className="text-sm font-mono font-bold text-[var(--sardis-orange)]">Sardis Wallet</span>
                <span className="text-xs text-muted-foreground">Policy Engine</span>
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
                    <span className="text-sm font-mono font-bold block">Direct</span>
                    <span className="text-xs text-muted-foreground">Instant transfer</span>
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
                description: "Fund agent wallets via provider-integrated ACH, wire, or card on-ramps.",
                details: ["Provider-specific pricing", "Design-partner sandbox lanes", "Policy checks before spend"]
              },
              {
                icon: icons.wallet,
                title: "Unified Balance",
                description: "One wallet balance powers everything — virtual cards, direct transfers, and merchant payouts.",
                details: ["Policy enforcement on all spend", "Real-time balance tracking", "Unified balance view"]
              },
              {
                icon: icons.creditCardGear,
                title: "USD Payouts",
                description: "Withdraw to any US bank account. Automatic compliance checks on every withdrawal.",
                details: ["Provider-dependent settlement timing", "Compliance gating", "Off-ramp status tracking"]
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
                    <CardTitle className="text-lg font-semibold font-display">{feature.title}</CardTitle>
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
              <span className="ml-4 text-sm font-mono text-muted-foreground">treasury.ts</span>
            </div>
            <div className="p-6 font-mono text-sm leading-relaxed bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] text-[var(--sardis-canvas)] overflow-x-auto">
              <pre className="whitespace-pre">{`import { SardisClient } from '@sardis/sdk'

const client = new SardisClient({ apiKey: 'sk_...' })

// ACH collection (fund treasury)
const funded = await client.treasury.fund({
  financial_account_token: 'fa_issuing_123',
  external_bank_account_token: 'eba_123',
  amount_minor: 100000, // $1,000.00
  method: 'ACH_NEXT_DAY',
  sec_code: 'CCD',
})

// ACH payment (withdraw)
const withdrawal = await client.treasury.withdraw({
  financial_account_token: 'fa_issuing_123',
  external_bank_account_token: 'eba_123',
  amount_minor: 50000, // $500.00
  method: 'ACH_NEXT_DAY',
  sec_code: 'CCD',
})

const balances = await client.treasury.getBalances()`}</pre>
            </div>
          </motion.div>
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
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-5">The Policy Firewall</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Others build payment rails. We build the intelligence layer that prevents financial hallucinations.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-6 mb-12">
            {[
              {
                icon: icons.policy,
                title: "Natural Language Policies",
                description: "Define complex spending rules in plain English. Not just limits—context-aware governance.",
                unique: true
              },
              {
                icon: icons.shieldLock,
                title: "Non-Custodial Security",
                description: "Your keys, your funds. No single entity — not even Sardis — can move money without your approval.",
                unique: false
              },
              {
                icon: icons.terminal,
                title: "Zero-Config MCP",
                description: "One command to add 50+ payment and treasury tools to Claude or Cursor. No setup required.",
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
                className="w-full md:w-[calc(50%-12px)] lg:w-[calc(33.333%-16px)]"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
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
                <h3 className="text-base font-semibold font-display mb-2">No competitor offers NL policies + approval queues + goal drift detection</h3>
                <p className="text-muted-foreground">We analyzed Locus, Payman, and Skyfire. They build rails — we build the intelligence layer. Read why.</p>
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
                fullName: "Trust Anchor Protocol",
                description: "Cryptographic identity verification. Agent attestation and credential chains.",
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
                    <CardTitle className="text-lg font-semibold font-display text-[var(--sardis-orange)]">{protocol.name}</CardTitle>
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
                <h3 className="text-base font-semibold font-display mb-1">x402 Micropayments</h3>
                <p className="text-muted-foreground">HTTP 402 Payment Required - Pay-per-API-call for agent services. Sub-cent transactions with instant settlement.</p>
              </div>
              <Badge variant="outline" className="text-emerald-600 border-emerald-600/30 rounded-none font-mono">
                Implemented
              </Badge>
            </div>
          </motion.div>
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
                  desc: "Spending limits, merchant rules, time windows — all checked before any money moves."
                },
                {
                  step: "03",
                  title: "Secure Signing",
                  desc: "Secure custody ensures no single entity can move funds. The agent never touches private keys."
                },
                {
                  step: "04",
                  title: "Settlement",
                  desc: "Payment executes via the optimal rail — virtual card, bank transfer, or direct settlement."
                }
              ].map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.12 }}
                  className="relative"
                >
                  {/* Step number circle */}
                  <div className="w-10 h-10 border-2 border-[var(--sardis-orange)] bg-background flex items-center justify-center mb-5 font-mono font-bold text-sm text-[var(--sardis-orange)]">
                    {item.step}
                  </div>
                  <h4 className="font-semibold font-display mb-2">{item.title}</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
                </motion.div>
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
            <Badge variant="outline" className="mb-4 text-[var(--sardis-rose-strong)] dark:text-[#f4d0df] border-[var(--sardis-rose-strong)]/30 dark:border-[#f4d0df]/30 rounded-none font-mono">USE CASES</Badge>
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">What Agents Can Do</h2>
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
                description: "Coordinate payments across agent teams. One agent discovers, another negotiates, a third executes payment — all with audit trails.",
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
            <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Contributing to the Ecosystem</h2>
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
                description: "Native integration with Claude, Cursor, and any MCP-compatible AI. 50+ tools for payments, wallets, treasury ACH, holds, invoices, and commerce.",
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
              <h3 className="text-lg font-semibold font-display mb-2">Install the SDKs</h3>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Our packages are live on npm and PyPI. Currently in developer preview — become a design partner for early access and an API key.
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
                    <div className="flex items-center gap-2">
                      <a href="https://pypi.org/user/sardis/" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-[var(--sardis-orange)] font-mono">pypi.org/user/sardis →</a>
                      <span className="text-xs font-mono px-1.5 py-0.5 bg-[var(--sardis-orange)]/10 text-[var(--sardis-orange)] border border-[var(--sardis-orange)]/20">4,600/mo</span>
                    </div>
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
                    <div className="flex items-center gap-2">
                      <a href="https://www.npmjs.com/org/sardis" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-[var(--sardis-orange)] font-mono">npmjs.com/org/sardis →</a>
                      <span className="text-xs font-mono px-1.5 py-0.5 bg-[var(--sardis-orange)]/10 text-[var(--sardis-orange)] border border-[var(--sardis-orange)]/20">2,190/mo</span>
                    </div>
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
              <h2 className="text-4xl md:text-5xl font-display font-semibold mb-4">Traction & Trust</h2>
              <p className="text-lg text-muted-foreground max-w-xl">
                SDKs published. Infrastructure battle-tested. Looking for design partners to shape the product together.
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
              { label: "MARKET", value: "$30T by 2030", sub: <span>Machine Customer Economy — <a href="https://www.forbes.com/sites/torconstantino/2025/02/18/machine-customers-ai-buyers-to-control-30-trillion-in-purchases-by-2030/" target="_blank" rel="noreferrer" className="underline hover:text-[var(--sardis-orange)]">Gartner via Forbes</a></span> },
              { label: "ADOPTION", value: "6,800+", sub: <span>monthly installs — <span className="text-foreground">2,190 npm</span> + <span className="text-foreground">4,600 PyPI</span> • 19 packages</span> },
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
          <h2 className="text-4xl md:text-5xl font-display font-semibold mb-6">Become a Design Partner</h2>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            We're looking for teams building AI agents that need payment capabilities. Get early access, hands-on support, and shape the product with us.
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
              <span>Policy-First</span>
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
