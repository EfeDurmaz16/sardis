import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Demo scenarios showing the "aha" moments
const DEMO_SCENARIOS = [
    { id: 'saas', label: '✓ OpenAI ($20)', expected: 'approved', color: 'emerald' },
    { id: 'giftcard', label: '✕ Amazon ($500)', expected: 'blocked', color: 'red' },
    { id: 'github', label: '✓ GitHub ($19)', expected: 'approved', color: 'emerald' },
    { id: 'crypto', label: '✕ Coinbase ($200)', expected: 'blocked', color: 'red' },
];

// Generate mock virtual card
const generateCard = () => ({
    number: `4242 •••• •••• ${Math.floor(1000 + Math.random() * 9000)}`,
    cvv: String(Math.floor(100 + Math.random() * 900)),
    expiry: '12/26',
});

const SardisPlayground = () => {
    const [terminalLogs, setTerminalLogs] = useState([
        { type: 'system', text: 'Sardis MCP Server v1.0.0 started...' },
        { type: 'system', text: 'Connected to Claude Desktop' },
        { type: 'agent', text: 'Agent ID: agent_0x7f4d...3a91' }
    ]);
    const [dashboardLogs, setDashboardLogs] = useState([]);
    const [status, setStatus] = useState('idle');
    const [virtualCard, setVirtualCard] = useState(null);
    const [activeScenario, setActiveScenario] = useState(null);
    const terminalRef = useRef(null);
    const dashboardRef = useRef(null);

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
            setDashboardLogs(prev => [...prev, { text: '✅ POLICY: ALLOWED', color: 'text-emerald-400 font-bold text-base' }]);
            await delay(300);
            setDashboardLogs(prev => [...prev, { text: 'MPC Signing... ✍️ Signed', color: 'text-emerald-300' }]);
            await delay(400);

            const card = generateCard();
            setVirtualCard(card);

            setDashboardLogs(prev => [...prev, { text: '💳 Virtual Card Issued', color: 'text-amber-400' }]);

            setStatus('success');
            const txId = `tx_${Math.random().toString(36).substring(2, 10)}`;
            setTerminalLogs(prev => [...prev,
                { type: 'system', text: 'Payment approved.' },
                { type: 'card', text: `Card: ${card.number}` },
                { type: 'success', text: `✓ Transaction ID: ${txId}` }
            ]);
        } else {
            // BLOCKED FLOW
            setDashboardLogs(prev => [...prev, { text: '❌ POLICY: BLOCKED', color: 'text-red-400 font-bold text-base' }]);
            await delay(200);
            setDashboardLogs(prev => [...prev, { text: `Reason: ${details.reason}`, color: 'text-red-300' }]);
            await delay(200);
            setDashboardLogs(prev => [...prev, { text: '🛡️ Financial Hallucination PREVENTED', color: 'text-amber-400 font-semibold' }]);

            setStatus('error');
            setTerminalLogs(prev => [...prev,
                { type: 'error', text: 'Error 403: Policy Violation' },
                { type: 'prevention', text: '🛡️ Financial Hallucination PREVENTED' }
            ]);
        }
    };

    const delay = (ms) => new Promise(r => setTimeout(r, ms));

    return (
        <div className="bg-zinc-950 rounded-2xl border border-white/10 shadow-2xl overflow-hidden relative group">
            {/* Header Bar */}
            <div className="bg-zinc-900/80 px-4 py-3 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500/70" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
                        <div className="w-3 h-3 rounded-full bg-green-500/70" />
                    </div>
                    <span className="text-xs text-zinc-500 font-mono">sardis-playground.local</span>
                </div>
                <button
                    onClick={resetSimulation}
                    className="text-xs text-zinc-500 hover:text-white px-2 py-1 rounded hover:bg-white/5 transition-colors"
                >
                    Reset
                </button>
            </div>

            <div className="p-6">
                {/* Policy Display */}
                <div className="mb-4 px-4 py-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-sm flex items-center justify-between">
                    <div>
                        <span className="text-indigo-400 font-semibold">Active Policy:</span>
                        <span className="text-zinc-300 ml-2 font-mono text-xs">Allow SaaS & DevTools only. Max $100/tx.</span>
                    </div>
                    <div className="flex items-center gap-1">
                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                        <span className="text-emerald-400 text-xs">Live</span>
                    </div>
                </div>

                {/* Scenario Buttons */}
                <div className="flex flex-wrap gap-2 mb-6 justify-center">
                    {DEMO_SCENARIOS.map((scenario) => (
                        <button
                            key={scenario.id}
                            onClick={() => runSimulation(scenario.id)}
                            disabled={status === 'processing'}
                            className={`px-4 py-2 rounded-lg transition-all text-sm font-medium disabled:opacity-50 active:scale-95 ${
                                activeScenario === scenario.id
                                    ? scenario.expected === 'approved'
                                        ? 'bg-emerald-600 text-white border border-emerald-400/50 shadow-[0_0_15px_rgba(16,185,129,0.3)]'
                                        : 'bg-red-600 text-white border border-red-400/50 shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                                    : scenario.expected === 'approved'
                                        ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/40'
                                        : 'bg-zinc-800 text-zinc-400 border border-white/10 hover:bg-zinc-700 hover:text-white'
                            }`}
                        >
                            {scenario.label}
                        </button>
                    ))}
                </div>

                {/* Panels Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-sm">
                    {/* Left Panel: Agent Terminal */}
                    <div className="bg-black/80 rounded-xl border border-white/5 overflow-hidden">
                        <div className="px-4 py-2 bg-zinc-900/50 border-b border-white/5 flex justify-between items-center">
                            <span className="text-zinc-600 text-[10px] uppercase tracking-widest">Agent Terminal (MCP)</span>
                            <span className={`px-2 py-0.5 rounded text-[9px] ${
                                status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-emerald-500/20 text-emerald-400'
                            }`}>
                                {status === 'processing' ? 'PROCESSING' : 'READY'}
                            </span>
                        </div>
                        <div ref={terminalRef} className="p-4 h-56 overflow-y-auto">
                            {terminalLogs.map((log, i) => (
                                <div key={i} className={`mb-1.5 leading-relaxed ${
                                    log.type === 'user' ? 'text-indigo-400' :
                                    log.type === 'error' ? 'text-red-400' :
                                    log.type === 'success' ? 'text-emerald-400 font-semibold' :
                                    log.type === 'card' ? 'text-amber-400' :
                                    log.type === 'prevention' ? 'text-amber-400 font-semibold' :
                                    log.type === 'agent' ? 'text-purple-400' : 'text-zinc-400'
                                }`}>
                                    <span className="opacity-50 select-none">{log.type === 'user' ? '>' : '$'}</span> {log.text}
                                </div>
                            ))}
                            {status === 'processing' && <div className="animate-pulse text-indigo-400/50 mt-1">█</div>}
                        </div>
                    </div>

                    {/* Right Panel: Policy Engine */}
                    <div className="bg-zinc-900/50 rounded-xl border border-white/5 overflow-hidden">
                        <div className="px-4 py-2 bg-zinc-800/50 border-b border-white/5">
                            <span className="text-zinc-600 text-[10px] uppercase tracking-widest">SARDIS POLICY ENGINE (CFO)</span>
                        </div>
                        <div ref={dashboardRef} className="p-4 h-40 overflow-y-auto">
                            {dashboardLogs.length === 0 && <div className="text-zinc-700 italic">Awaiting transaction request...</div>}
                            {dashboardLogs.map((log, i) => (
                                <motion.div
                                    initial={{ opacity: 0, x: -5 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    key={i}
                                    className={`mb-1.5 leading-relaxed ${log.color || 'text-zinc-300'}`}
                                >
                                    <span className="text-zinc-700 text-[10px] select-none">[{new Date().toLocaleTimeString([], { hour12: false })}]</span> {log.text}
                                </motion.div>
                            ))}
                        </div>

                        {/* Virtual Card Display */}
                        <AnimatePresence>
                            {virtualCard && (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -10 }}
                                    className="mx-4 mb-4 p-3 rounded-lg bg-gradient-to-r from-indigo-600/20 to-purple-600/20 border border-indigo-500/30"
                                >
                                    <div className="text-[10px] uppercase tracking-wider text-indigo-400 mb-1">Virtual Card</div>
                                    <div className="font-mono text-white">{virtualCard.number}</div>
                                    <div className="flex gap-4 text-xs text-zinc-400 mt-1">
                                        <span>CVV: {virtualCard.cvv}</span>
                                        <span>Exp: {virtualCard.expiry}</span>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="bg-black/30 px-4 py-2 border-t border-white/5 flex items-center justify-between text-xs text-zinc-600">
                <span>Powered by MPC • Non-Custodial • Multi-Chain</span>
                <span>Try the demo above ↑</span>
            </div>

            {/* Background Glow */}
            <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none group-hover:bg-indigo-500/20 transition-colors duration-700" />
        </div>
    );
};

export default SardisPlayground;
