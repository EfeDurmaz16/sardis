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
function IsometricIcon({ src, alt = "", className = "" }) {
  return (
    <img
      src={src}
      alt={alt}
      className={cn("w-8 h-8 object-contain drop-shadow-sm", className)}
      style={{ filter: "drop-shadow(0 0 1px rgba(0,0,0,0.3))" }}
    />
  );
}

function App() {
  const [scrolled, setScrolled] = useState(false);
  const [isDark, setIsDark] = useState(true);

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
            <div className="w-8 h-8 bg-[var(--sardis-orange)] flex items-center justify-center text-white font-bold">
              S
            </div>
            <span>Sardis</span>
          </div>

          <div className="hidden md:flex items-center gap-1">
            <Badge variant="outline" className="mr-6 border-emerald-600 text-emerald-600 dark:text-emerald-400 dark:border-emerald-400 bg-transparent px-3 py-1 rounded-none">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 animate-pulse" />
              LIVE ON TESTNET
            </Badge>
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none" asChild>
              <Link to="/docs">Docs</Link>
            </Button>
            <Button variant="ghost" className="text-muted-foreground hover:text-foreground rounded-none">GitHub</Button>
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <Button className="ml-2 bg-[var(--sardis-orange)] text-white hover:bg-[var(--sardis-orange)]/90 font-medium rounded-none">
              Get Early Access
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
              <CopyCommand command="npx @sardis/mcp-server start" />
              <div className="flex flex-col sm:flex-row items-center gap-4 mt-4">
                <Button size="lg" className="h-14 px-8 text-lg rounded-none bg-[var(--sardis-orange)] hover:bg-[var(--sardis-orange)]/90 text-white font-medium">
                  Get Early Access
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
                      <IsometricIcon src={item.icon} className="w-6 h-6" />
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

          <div className="grid md:grid-cols-3 gap-6">
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
                description: "Real-time settlement via stablecoins (USDC) and fiat rails. No waiting days."
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
                      <IsometricIcon src={feature.icon} className="w-10 h-10" />
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
              href="https://sepolia.etherscan.io/address/0xAb849f77D54d4D406ED5082079cB44EfC22EAa98"
              target="_blank"
              rel="noreferrer"
              className="group flex items-center gap-3 px-5 py-3 border border-border hover:border-[var(--sardis-orange)] transition-colors"
            >
              <div className="w-8 h-8 border border-border group-hover:border-[var(--sardis-orange)] flex items-center justify-center">
                <IsometricIcon src={icons.searchInsights} className="w-5 h-5" />
              </div>
              <div className="text-sm text-left">
                <div className="text-xs text-muted-foreground uppercase tracking-wider font-mono font-semibold">Verify on Etherscan</div>
                <div className="font-mono text-foreground group-hover:text-[var(--sardis-orange)] transition-colors">0xAb84...Aa98</div>
              </div>
            </a>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              { label: "INFRASTRUCTURE", value: "Live on Sepolia", sub: "Core infra running" },
              { label: "TIMELINE", value: "Q1 2026", sub: "Mainnet Launch" },
              { label: "BACKING", value: "Founder Institute", sub: "QNB Pilot Discussions" }
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
          <h2 className="text-3xl md:text-5xl font-display font-bold mb-6">Join the Alpha Design Partner Program</h2>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
            Be among the first to give your agents financial autonomy. Early partners get hands-on support and priority access.
          </p>
          <WaitlistForm />
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="container mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 bg-[var(--sardis-orange)] flex items-center justify-center text-white font-bold text-xs">
              S
            </div>
            <span className="font-bold font-display">Sardis</span>
          </div>

          <div className="flex gap-8 text-sm text-muted-foreground font-mono">
            <span>Non-Custodial</span>
            <span>Multi-Chain</span>
            <span>AP2 Compliant</span>
          </div>

          <div className="text-sm text-muted-foreground font-mono">
            © 2026 Sardis. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
