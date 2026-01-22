import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, useAnimation } from 'framer-motion';

// Demo scenarios showing the "aha" moments
const DEMO_SCENARIOS = [
    { id: 'saas', label: 'OpenAI ($20)', expected: 'approved', status: 'ALLOW' },
    { id: 'giftcard', label: 'Amazon ($500)', expected: 'blocked', status: 'BLOCK' },
    { id: 'github', label: 'GitHub ($19)', expected: 'approved', status: 'ALLOW' },
    { id: 'crypto', label: 'Coinbase ($200)', expected: 'blocked', status: 'BLOCK' },
];

// Generate mock virtual card
const generateCard = () => ({
    number: `4242 •••• •••• ${Math.floor(1000 + Math.random() * 9000)}`,
    cvv: String(Math.floor(100 + Math.random() * 900)),
    expiry: '12/26',
});

// Typewriter component for terminal output
const TypewriterText = ({ text, speed = 20, onComplete, className = '' }) => {
    const [displayText, setDisplayText] = useState('');
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (currentIndex < text.length) {
            const timeout = setTimeout(() => {
                setDisplayText(prev => prev + text[currentIndex]);
                setCurrentIndex(prev => prev + 1);
            }, speed);
            return () => clearTimeout(timeout);
        } else if (onComplete) {
            onComplete();
        }
    }, [currentIndex, text, speed, onComplete]);

    return <span className={className}>{displayText}</span>;
};

// Confetti particle for success animation
const Confetti = ({ count = 20 }) => {
    const colors = ['#ef8354', '#22c55e', '#3b82f6', '#a855f7', '#eab308'];
    const particles = Array.from({ length: count }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        color: colors[Math.floor(Math.random() * colors.length)],
        delay: Math.random() * 0.3,
        duration: 1 + Math.random() * 0.5,
    }));

    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {particles.map(p => (
                <motion.div
                    key={p.id}
                    className="absolute w-2 h-2"
                    style={{
                        left: `${p.x}%`,
                        backgroundColor: p.color,
                        top: '-10px',
                    }}
                    initial={{ opacity: 1, y: 0, rotate: 0 }}
                    animate={{
                        opacity: [1, 1, 0],
                        y: [0, 150, 200],
                        rotate: [0, 180, 360],
                        x: [0, (Math.random() - 0.5) * 100],
                    }}
                    transition={{
                        duration: p.duration,
                        delay: p.delay,
                        ease: 'easeOut',
                    }}
                />
            ))}
        </div>
    );
};

// Shake animation variants
const shakeAnimation = {
    shake: {
        x: [0, -10, 10, -10, 10, -5, 5, 0],
        transition: { duration: 0.5 },
    },
};

const SardisPlayground = () => {
    const [terminalLogs, setTerminalLogs] = useState([
        { type: 'system', text: 'Sardis MCP Server v1.0.0 started...', instant: true },
        { type: 'system', text: 'Connected to Claude Desktop', instant: true },
        { type: 'agent', text: 'Agent ID: agent_0x7f4d...3a91', instant: true }
    ]);
    const [dashboardLogs, setDashboardLogs] = useState([]);
    const [status, setStatus] = useState('idle');
    const [virtualCard, setVirtualCard] = useState(null);
    const [activeScenario, setActiveScenario] = useState(null);
    const [showConfetti, setShowConfetti] = useState(false);
    const [isFlipped, setIsFlipped] = useState(false);
    const terminalRef = useRef(null);
    const dashboardRef = useRef(null);
    const panelControls = useAnimation();

    // Auto-scroll
    useEffect(() => {
        if (terminalRef.current) terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }, [terminalLogs]);

    useEffect(() => {
        if (dashboardRef.current) dashboardRef.current.scrollTop = dashboardRef.current.scrollHeight;
    }, [dashboardLogs]);

    const resetSimulation = () => {
        setTerminalLogs([
            { type: 'system', text: 'Sardis MCP Server v1.0.0 started...' },
            { type: 'system', text: 'Connected to Claude Desktop' },
            { type: 'agent', text: 'Agent ID: agent_0x7f4d...3a91' }
        ]);
        setDashboardLogs([]);
        setStatus('idle');
        setVirtualCard(null);
        setActiveScenario(null);
    };

    const getScenarioDetails = (scenarioId) => {
        const scenarios = {
            saas: { vendor: 'OpenAI', amount: 20, category: 'SaaS', approved: true },
            giftcard: { vendor: 'Amazon', amount: 500, category: 'Retail/Gift Cards', approved: false, reason: 'Retail marketplace not in allowlist' },
            github: { vendor: 'GitHub', amount: 19, category: 'DevTools', approved: true },
            crypto: { vendor: 'Coinbase', amount: 200, category: 'Crypto Exchange', approved: false, reason: 'Amount exceeds $100 limit' },
        };
        return scenarios[scenarioId];
    };

    const runSimulation = async (scenarioId) => {
        if (status === 'processing') return;

        setStatus('processing');
        setActiveScenario(scenarioId);
        setVirtualCard(null);
        setDashboardLogs([]);

        const details = getScenarioDetails(scenarioId);
        const command = `sardis.pay("${details.vendor}", $${details.amount})`;

        // Agent command
        setTerminalLogs(prev => [...prev, { type: 'user', text: command }]);

        await delay(400);

        // Dashboard processing
        const steps = [
            { text: `Request: ${details.vendor} ($${details.amount})`, delay: 300 },
            { text: `Category: ${details.category}`, delay: 400 },
            { text: 'Running policy check...', delay: 500 },
        ];

        for (let step of steps) {
            await delay(step.delay);
            setDashboardLogs(prev => [...prev, { text: step.text }]);
        }

        await delay(400);

        if (details.approved) {
            // APPROVED FLOW
            setDashboardLogs(prev => [...prev, { text: 'POLICY: ALLOWED', color: 'text-emerald-500 font-bold text-base', approved: true }]);
            await delay(300);
            setDashboardLogs(prev => [...prev, { text: 'MPC Signing... Signed', color: 'text-emerald-400' }]);
            await delay(400);

            const card = generateCard();
            setVirtualCard(card);

            setDashboardLogs(prev => [...prev, { text: 'Virtual Card Issued', color: 'text-[var(--sardis-orange)]' }]);

            setStatus('success');
            setShowConfetti(true);
            setTimeout(() => setShowConfetti(false), 2000);

            const txId = `tx_${Math.random().toString(36).substring(2, 10)}`;
            setTerminalLogs(prev => [...prev,
                { type: 'system', text: 'Payment approved.' },
                { type: 'card', text: `Card: ${card.number}` },
                { type: 'success', text: `Transaction ID: ${txId}` }
            ]);
        } else {
            // BLOCKED FLOW
            setDashboardLogs(prev => [...prev, { text: 'POLICY: BLOCKED', color: 'text-red-500 font-bold text-base', blocked: true }]);
            await delay(200);
            setDashboardLogs(prev => [...prev, { text: `Reason: ${details.reason}`, color: 'text-red-400' }]);
            await delay(200);
            setDashboardLogs(prev => [...prev, { text: 'Financial Hallucination PREVENTED', color: 'text-[var(--sardis-orange)] font-semibold' }]);

            setStatus('error');
            panelControls.start('shake');
            setTerminalLogs(prev => [...prev,
                { type: 'error', text: 'Error 403: Policy Violation' },
                { type: 'prevention', text: 'Financial Hallucination PREVENTED' }
            ]);
        }
    };

    const delay = (ms) => new Promise(r => setTimeout(r, ms));

    return (
        <div className="bg-card border border-border overflow-hidden relative group">
            {/* Confetti on success */}
            <AnimatePresence>
                {showConfetti && <Confetti count={30} />}
            </AnimatePresence>

            {/* Header Bar */}
            <div className="bg-muted px-4 py-3 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 bg-red-500" />
                        <div className="w-3 h-3 bg-yellow-500" />
                        <div className="w-3 h-3 bg-emerald-500" />
                    </div>
                    <span className="text-xs text-muted-foreground font-mono">sardis-playground.local</span>
                </div>
                <button
                    onClick={resetSimulation}
                    className="text-xs text-muted-foreground hover:text-foreground px-3 py-1 border border-border hover:border-[var(--sardis-orange)] transition-colors font-mono"
                >
                    RESET
                </button>
            </div>

            <div className="p-6">
                {/* Policy Display */}
                <div className="mb-4 px-4 py-3 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-sm flex items-center justify-between">
                    <div>
                        <span className="text-[var(--sardis-orange)] font-semibold font-mono">ACTIVE POLICY:</span>
                        <span className="text-foreground ml-2 font-mono text-xs">Allow SaaS & DevTools only. Max $100/tx.</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-emerald-500 animate-pulse" />
                        <span className="text-emerald-500 text-xs font-mono font-bold">LIVE</span>
                    </div>
                </div>

                {/* Scenario Buttons */}
                <div className="flex flex-wrap gap-2 mb-6 justify-center">
                    {DEMO_SCENARIOS.map((scenario) => (
                        <button
                            key={scenario.id}
                            onClick={() => runSimulation(scenario.id)}
                            disabled={status === 'processing'}
                            className={`px-4 py-2 transition-all text-sm font-mono font-medium disabled:opacity-50 active:scale-95 border ${
                                activeScenario === scenario.id
                                    ? scenario.expected === 'approved'
                                        ? 'bg-emerald-600 text-white border-emerald-500'
                                        : 'bg-red-600 text-white border-red-500'
                                    : scenario.expected === 'approved'
                                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20 hover:border-emerald-500'
                                        : 'bg-card text-muted-foreground border-border hover:border-[var(--sardis-orange)] hover:text-foreground'
                            }`}
                        >
                            [{scenario.status}] {scenario.label}
                        </button>
                    ))}
                </div>

                {/* Panels Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-sm">
                    {/* Left Panel: Agent Terminal */}
                    <motion.div
                        variants={shakeAnimation}
                        animate={panelControls}
                        className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border overflow-hidden">
                        <div className="px-4 py-2 bg-[#1f1e1c] border-b border-border flex justify-between items-center">
                            <span className="text-[var(--sardis-canvas)]/50 text-[10px] uppercase tracking-widest">Agent Terminal (MCP)</span>
                            <span className={`px-2 py-0.5 text-[9px] font-bold border ${
                                status === 'processing'
                                    ? 'border-yellow-500/50 text-yellow-400'
                                    : 'border-emerald-500/50 text-emerald-400'
                            }`}>
                                {status === 'processing' ? 'PROCESSING' : 'READY'}
                            </span>
                        </div>
                        <div ref={terminalRef} className="p-4 h-56 overflow-y-auto text-[var(--sardis-canvas)]">
                            {terminalLogs.map((log, i) => (
                                <div key={i} className={`mb-1.5 leading-relaxed ${
                                    log.type === 'user' ? 'text-[var(--sardis-orange)]' :
                                    log.type === 'error' ? 'text-red-400' :
                                    log.type === 'success' ? 'text-emerald-400 font-semibold' :
                                    log.type === 'card' ? 'text-[var(--sardis-orange)]' :
                                    log.type === 'prevention' ? 'text-[var(--sardis-orange)] font-semibold' :
                                    log.type === 'agent' ? 'text-purple-400' : 'text-[var(--sardis-canvas)]/60'
                                }`}>
                                    <span className="opacity-50 select-none">{log.type === 'user' ? '>' : '$'}</span> {log.text}
                                </div>
                            ))}
                            {status === 'processing' && <div className="animate-pulse text-[var(--sardis-orange)]/50 mt-1">█</div>}
                        </div>
                    </motion.div>

                    {/* Right Panel: Policy Engine */}
                    <motion.div
                        variants={shakeAnimation}
                        animate={panelControls}
                        className="bg-card border border-border overflow-hidden">
                        <div className="px-4 py-2 bg-muted border-b border-border">
                            <span className="text-muted-foreground text-[10px] uppercase tracking-widest font-mono">SARDIS POLICY ENGINE (CFO)</span>
                        </div>
                        <div ref={dashboardRef} className="p-4 h-40 overflow-y-auto">
                            {dashboardLogs.length === 0 && <div className="text-muted-foreground italic">Awaiting transaction request...</div>}
                            {dashboardLogs.map((log, i) => (
                                <motion.div
                                    initial={{ opacity: 0, x: log.blocked ? 10 : -5, scale: log.approved ? 0.95 : 1 }}
                                    animate={log.blocked ? {
                                        opacity: 1,
                                        x: [10, -5, 5, -3, 0],
                                        backgroundColor: ['rgba(239, 68, 68, 0.2)', 'rgba(239, 68, 68, 0)'],
                                    } : log.approved ? {
                                        opacity: 1,
                                        x: 0,
                                        scale: [0.95, 1.02, 1],
                                        backgroundColor: ['rgba(16, 185, 129, 0.2)', 'rgba(16, 185, 129, 0)'],
                                    } : { opacity: 1, x: 0 }}
                                    transition={log.blocked || log.approved ? { duration: 0.5 } : { duration: 0.2 }}
                                    key={i}
                                    className={`mb-1.5 leading-relaxed ${log.color || 'text-foreground'} ${log.blocked || log.approved ? 'px-2 py-1 -mx-2' : ''}`}
                                >
                                    <span className="text-muted-foreground text-[10px] select-none">[{new Date().toLocaleTimeString([], { hour12: false })}]</span> {log.text}
                                </motion.div>
                            ))}
                        </div>

                        {/* Virtual Card Display with Flip Animation */}
                        <AnimatePresence>
                            {virtualCard && (
                                <div className="mx-4 mb-4" style={{ perspective: '1000px' }}>
                                    <motion.div
                                        initial={{ rotateY: 180, opacity: 0 }}
                                        animate={{ rotateY: 0, opacity: 1 }}
                                        exit={{ rotateY: -180, opacity: 0 }}
                                        transition={{ duration: 0.6, ease: 'easeOut' }}
                                        className="p-3 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 backface-hidden"
                                        style={{ transformStyle: 'preserve-3d' }}
                                    >
                                        <div className="text-[10px] uppercase tracking-wider text-[var(--sardis-orange)] mb-1 font-bold flex items-center gap-2">
                                            <motion.span
                                                initial={{ scale: 0 }}
                                                animate={{ scale: 1 }}
                                                transition={{ delay: 0.3, type: 'spring', stiffness: 500 }}
                                            >
                                                ✓
                                            </motion.span>
                                            Virtual Card Issued
                                        </div>
                                        <motion.div
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: 0.4 }}
                                            className="font-mono text-foreground"
                                        >
                                            {virtualCard.number}
                                        </motion.div>
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            transition={{ delay: 0.5 }}
                                            className="flex gap-4 text-xs text-muted-foreground mt-1"
                                        >
                                            <span>CVV: {virtualCard.cvv}</span>
                                            <span>Exp: {virtualCard.expiry}</span>
                                        </motion.div>
                                    </motion.div>
                                </div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                </div>
            </div>

            {/* Footer */}
            <div className="bg-muted px-4 py-2 border-t border-border flex items-center justify-between text-xs text-muted-foreground font-mono">
                <span>Powered by MPC • Non-Custodial • Multi-Chain</span>
                <span>Try the demo above</span>
            </div>
        </div>
    );
};

export default SardisPlayground;
