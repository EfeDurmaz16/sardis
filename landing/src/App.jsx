import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Robot,
  ShieldCheck,
  Lightning,
  Wallet,
  ChartLineUp,
  Globe,
  Code,
  ArrowRight,
  CheckCircle,
  Cube,
  Stack,
  Lock,
  IdentificationCard,
  Bank,
  Cpu,
  ArrowSquareOut
} from "@phosphor-icons/react";
import { IconContext } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

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

function App() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <IconContext.Provider
      value={{
        size: 32,
        weight: "duotone",
        mirrored: false,
      }}
    >
      <div className="min-h-screen bg-background text-foreground overflow-x-hidden font-sans selection:bg-primary/20">

        {/* Navigation */}
        <nav
          className={cn(
            "fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b border-transparent",
            scrolled ? "bg-background/80 backdrop-blur-md border-border/50 py-3" : "py-6 bg-transparent"
          )}
        >
          <div className="container mx-auto px-6 flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold text-xl tracking-tight">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white">
                <Cube weight="fill" size={20} />
              </div>
              <span className="font-display">Sardis</span>
            </div>

            <div className="hidden md:flex items-center gap-1">
              <Badge variant="outline" className="mr-6 border-emerald-500/30 text-emerald-400 bg-emerald-500/5 px-3 py-1">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full mr-2 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                LIVE ON TESTNET
              </Badge>
              <Button variant="ghost" className="text-muted-foreground hover:text-foreground">Docs</Button>
              <Button variant="ghost" className="text-muted-foreground hover:text-foreground">GitHub</Button>
              <Button className="ml-2 bg-white text-black hover:bg-white/90 font-medium">
                Get Early Access
              </Button>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="relative pt-32 pb-20 md:pt-48 md:pb-32 overflow-hidden">
          {/* Background Elements */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-7xl pointer-events-none">
            <div className="absolute top-20 left-1/4 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] mix-blend-screen opacity-30 animate-pulse" style={{ animationDuration: '4s' }} />
            <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-accent/20 rounded-full blur-[120px] mix-blend-screen opacity-20" />
          </div>

          <div className="container mx-auto px-6 relative z-10">
            <motion.div
              initial="initial"
              animate="animate"
              variants={staggerContainer}
              className="max-w-4xl mx-auto text-center"
            >
              <motion.div variants={fadeInUp} className="flex justify-center mb-8">
                <Badge variant="secondary" className="px-4 py-1.5 rounded-full text-sm font-medium border border-white/10 bg-white/5 backdrop-blur-sm">
                  🚀 Building the $30 Trillion Machine Customer Economy
                </Badge>
              </motion.div>

              <motion.h1 variants={fadeInUp} className="text-5xl md:text-7xl font-display font-bold leading-tight tracking-tight mb-8">
                The Payment Execution Layer for <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">AI Agents</span>
              </motion.h1>

              <motion.p variants={fadeInUp} className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
                We give AI agents non-custodial wallets and spending policies so they can finally execute transactions, not just plan them.
              </motion.p>

              <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button size="lg" className="h-14 px-8 text-lg rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-[0_0_30px_rgba(99,102,241,0.3)] transition-all duration-300 hover:scale-105">
                  Start Building
                  <ArrowRight weight="bold" className="ml-2" />
                </Button>
                <Button size="lg" variant="outline" className="h-14 px-8 text-lg rounded-full border-white/10 bg-white/5 hover:bg-white/10 backdrop-blur-lg">
                  <Stack className="mr-2" />
                  View Architecture
                </Button>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* Separator */}
        <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent w-full" />

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
                  They can plan complex workflows but <strong className="text-white font-medium">fail at checkout</strong> because current payment rails (2FA, OTPs, CAPTCHAs) block non-human actors.
                </p>

                <ul className="space-y-4">
                  {[
                    "Agents get blocked by SMS 2FA",
                    "No spending limits or guardrails",
                    "Impossible to audit agent spending"
                  ].map((item, i) => (
                    <li key={i} className="flex items-center gap-3 text-lg text-red-200/80">
                      <div className="w-6 h-6 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20">
                        <Lock size={14} className="text-red-400" weight="bold" />
                      </div>
                      {item}
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
                <div className="rounded-xl border border-white/10 bg-black/50 backdrop-blur-md overflow-hidden shadow-2xl">
                  <div className="bg-white/5 px-4 py-3 border-b border-white/5 flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/50" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                    <div className="w-3 h-3 rounded-full bg-green-500/50" />
                  </div>
                  <div className="p-6 font-mono text-sm leading-relaxed">
                    <div className="text-emerald-400 mb-2">$ agent plan trip --budget 500</div>
                    <div className="text-zinc-400 mb-4">{`> Planning itinerary... Done.`}</div>
                    <div className="text-emerald-400 mb-2">$ agent book flights</div>
                    <div className="text-zinc-400 mb-4">{`> Selecting best flight... UA445 selected.`}</div>
                    <div className="text-zinc-400 mb-2">{`> Entering payment details...`}</div>
                    <div className="text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20">
                      {`ERROR: 2FA Required. Please enter the code sent to +1 (555) ***-****`}
                      <br />
                      {`> Timeout. Booking failed.`}
                    </div>
                  </div>
                </div>

                {/* Floating badge */}
                <div className="absolute -bottom-6 -left-6 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg font-bold rotate-[-3deg] border border-red-400 text-sm">
                  🚫 EXECUTION BLOCKED
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Features Section: Banking for Bots */}
        <section className="py-24 bg-gradient-to-b from-transparent to-[#12121a]/50">
          <div className="container mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">Banking for Bots</h2>
              <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
                Sardis issues <span className="text-white font-medium">non-custodial</span> programmable wallets and virtual cards purpose-built for AI agents.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                {
                  icon: <Robot className="text-indigo-400" />,
                  title: "Autonomous Execution",
                  description: "Bypass human-centric 2FA barriers with MPC-secured signing. Agents can finally pay."
                },
                {
                  icon: <ShieldCheck className="text-emerald-400" />,
                  title: "Policy Engine",
                  description: "Set strict limits: 'Max $50/tx, $500/day, only these merchants.' Programmable trust."
                },
                {
                  icon: <Lightning className="text-amber-400" />,
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
                  <Card className="h-full bg-white/5 border-white/10 backdrop-blur-sm hover:border-indigo-500/30 hover:bg-white/10 transition-all duration-300 group">
                    <CardHeader>
                      <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                        {feature.icon}
                      </div>
                      <CardTitle className="text-xl font-bold">{feature.title}</CardTitle>
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
        <section className="py-24 border-y border-white/5 bg-black/30">
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
                className="group flex items-center gap-3 px-5 py-3 rounded-lg bg-[#12121a] border border-white/10 hover:border-indigo-500/50 transition-colors"
              >
                <div className="p-1.5 rounded bg-indigo-500/20 text-indigo-400">
                  <ArrowSquareOut weight="bold" />
                </div>
                <div className="text-sm text-left">
                  <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Verify on Etherscan</div>
                  <div className="font-mono text-zinc-300 group-hover:text-indigo-300 transition-colors">0xAb84...Aa98</div>
                </div>
              </a>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {[
                { label: "INFRASTRUCTURE", value: "Live on Sepolia", sub: "Core infra running" },
                { label: "TIMELINE", value: "Q1 2026", sub: "Mainnet Launch" },
                { label: "BACKING", value: "Founder Institute", sub: "QNB Pilot Discussions" }
              ].map((stat, i) => (
                <div key={i} className="p-8 rounded-2xl bg-gradient-to-br from-white/5 to-transparent border border-white/10">
                  <div className="text-xs font-bold tracking-widest text-indigo-400 mb-2 text-opacity-80">{stat.label}</div>
                  <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-sm text-zinc-500 font-medium bg-zinc-900/50 inline-block px-2 py-0.5 rounded border border-white/5">{stat.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Founder Section */}
        <section className="py-24">
          <div className="container mx-auto px-6">
            <div className="max-w-4xl mx-auto rounded-3xl bg-gradient-to-br from-[#1b1b26] to-[#0f0f13] border border-white/10 p-8 md:p-12 relative overflow-hidden">
              {/* Decorative quote mark */}
              <div className="absolute top-8 right-8 text-white/5 font-serif text-9xl leading-none">"</div>

              <div className="flex flex-col md:flex-row gap-8 items-start relative z-10">
                <Avatar className="w-24 h-24 md:w-32 md:h-32 border-2 border-indigo-500/50">
                  <AvatarImage src="/efe-avatar.png" />
                  <AvatarFallback className="bg-indigo-950 text-indigo-200 text-2xl font-bold">ED</AvatarFallback>
                </Avatar>

                <div className="flex-1">
                  <blockquote className="text-xl md:text-2xl font-medium leading-relaxed mb-6 text-zinc-200">
                    "I hit this wall myself while building AI agents for the past 18 months. I'm building Sardis to solve the execution gap I faced as an engineer."
                  </blockquote>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-white/10 pt-6">
                    <div>
                      <div className="font-bold text-lg text-white">Efe Baran Durmaz</div>
                      <div className="text-indigo-400">AI Architect & Engineer</div>
                    </div>

                    <div className="flex gap-3">
                      <Button variant="outline" size="sm" className="h-9 gap-2" asChild>
                        <a href="https://linkedin.com/in/efe-baran-durmaz" target="_blank" rel="noreferrer">
                          <span className="font-bold">in</span> LinkedIn
                        </a>
                      </Button>
                      <Button variant="outline" size="sm" className="h-9 gap-2" asChild>
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
        <section className="py-24 text-center">
          <div className="container mx-auto px-6">
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-6">Start building autonomous commerce</h2>
            <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto">
              Join the developers building the first generation of agents that can effectively participate in the economy.
            </p>
            <Button size="lg" className="h-14 px-10 text-lg rounded-full bg-white text-black hover:bg-zinc-200 shadow-xl shadow-white/10 transition-all hover:scale-105">
              Request API Access
            </Button>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 border-t border-white/5 bg-[#050508]">
          <div className="container mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-2 opacity-50">
              <Cube weight="fill" size={24} />
              <span className="font-bold">Sardis</span>
            </div>

            <div className="flex gap-8 text-sm text-zinc-500">
              <span>Non-Custodial</span>
              <span>Multi-Chain</span>
              <span>AP2 Compliant</span>
            </div>

            <div className="text-sm text-zinc-600">
              © 2026 Sardis. All rights reserved.
            </div>
          </div>
        </footer>
      </div>
    </IconContext.Provider>
  );
}

export default App;
