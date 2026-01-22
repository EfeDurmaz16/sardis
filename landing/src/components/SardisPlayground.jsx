import React, { useState } from 'react';
import { motion } from 'framer-motion';

const SardisPlayground = () => {
    const [terminalLogs, setTerminalLogs] = useState([
        { type: 'system', text: 'Sardis MCP Server v1.0.0 started...' },
        { type: 'system', text: 'Connected to Claude Desktop' },
        { type: 'agent', text: 'Agent ID: agent_0x7f4d...3a91' }
    ]);
    const [dashboardLogs, setDashboardLogs] = useState([]);
    const [status, setStatus] = useState('idle'); // idle, processing, success, error
    const [currentPolicy, setCurrentPolicy] = useState('Allow SaaS & DevTools only. Max $100/tx.');

    const resetSimulation = () => {
        setTerminalLogs([
            { type: 'system', text: 'Sardis MCP Server v1.0.0 started...' },
            { type: 'system', text: 'Connected to Claude Desktop' },
            { type: 'agent', text: 'Agent ID: agent_0x7f4d...3a91' }
        ]);
        setDashboardLogs([]);
        setStatus('idle');
    };

    const runSimulation = async (type) => {
        setStatus('processing');

        // Terminal Log
        const command = type === 'saas' ? 'sardis.pay("OpenAI", $20, "API Credits")' : 'sardis.pay("Amazon", $500, "Gift Card")';
        setTerminalLogs(prev => [...prev, { type: 'user', text: command }]);

        // Dashboard Logs with timestamps
        const steps = [
            { text: `Request: ${type === 'saas' ? 'OpenAI ($20)' : 'Amazon ($500)'}`, delay: 400 },
            { text: `Merchant: ${type === 'saas' ? 'openai.com' : 'amazon.com'}`, delay: 600 },
            { text: 'Running policy check...', delay: 800 },
        ];

        for (let step of steps) {
            await new Promise(r => setTimeout(r, step.delay));
            setDashboardLogs(prev => [...prev, { text: step.text }]);
        }

        await new Promise(r => setTimeout(r, 600));

        if (type === 'saas') {
            setDashboardLogs(prev => [...prev, { text: 'Category: SaaS/DevTools', color: 'text-zinc-400' }]);
            await new Promise(r => setTimeout(r, 300));
            setDashboardLogs(prev => [...prev, { text: '✅ POLICY: ALLOWED', color: 'text-emerald-400 font-bold' }]);
            await new Promise(r => setTimeout(r, 400));
            setDashboardLogs(prev => [...prev, { text: 'MPC Signing... ✍️ Signed', color: 'text-emerald-300' }]);
            setStatus('success');
            setTerminalLogs(prev => [...prev,
                { type: 'system', text: 'Payment approved.' },
                { type: 'system', text: 'Card: 4242 •••• •••• 9999 | CVV: 847' },
                { type: 'success', text: '✓ Transaction ID: tx_0x8a2f...c91e' }
            ]);
        } else {
            setDashboardLogs(prev => [...prev, { text: 'Category: Retail/Gift Cards', color: 'text-zinc-400' }]);
            await new Promise(r => setTimeout(r, 300));
            setDashboardLogs(prev => [...prev, { text: '❌ POLICY: BLOCKED', color: 'text-red-400 font-bold' }]);
            await new Promise(r => setTimeout(r, 200));
            setDashboardLogs(prev => [...prev, { text: 'Reason: Merchant not in allowlist', color: 'text-red-300' }]);
            setStatus('error');
            setTerminalLogs(prev => [...prev,
                { type: 'error', text: 'Error 403: Policy Violation' },
                { type: 'error', text: 'Financial Hallucination PREVENTED' }
            ]);
        }
    };

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
                {/* Current Policy Display */}
                <div className="mb-4 px-4 py-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-sm">
                    <span className="text-indigo-400 font-semibold">Active Policy:</span>
                    <span className="text-zinc-300 ml-2 font-mono text-xs">{currentPolicy}</span>
                </div>

                {/* Simulation Controls */}
                <div className="flex flex-wrap gap-3 mb-6 justify-center">
                    <button
                        onClick={() => runSimulation('saas')}
                        disabled={status === 'processing'}
                        className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-all border border-emerald-400/50 shadow-[0_0_15px_rgba(16,185,129,0.2)] disabled:opacity-50 active:scale-95 font-medium text-sm"
                    >
                        ✓ Pay OpenAI ($20)
                    </button>
                    <button
                        onClick={() => runSimulation('giftcard')}
                        disabled={status === 'processing'}
                        className="px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition-all border border-white/10 disabled:opacity-50 active:scale-95 font-medium text-sm"
                    >
                        ✕ Pay Amazon ($500)
                    </button>
                </div>

                {/* Panels Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-sm">
                    {/* Left Panel: The Agent Terminal */}
                    <div className="bg-black/80 p-4 rounded-xl border border-white/5 h-64 overflow-y-auto shadow-inner">
                        <div className="text-zinc-600 text-[10px] uppercase tracking-widest mb-3 border-b border-white/5 pb-2 flex justify-between items-center">
                            <span>Agent Terminal (MCP)</span>
                            <span className={`px-2 py-0.5 rounded text-[9px] ${status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                                {status === 'processing' ? 'PROCESSING' : 'READY'}
                            </span>
                        </div>
                        {terminalLogs.map((log, i) => (
                            <div key={i} className={`mb-1.5 leading-relaxed ${
                                log.type === 'user' ? 'text-indigo-400' :
                                log.type === 'error' ? 'text-red-400' :
                                log.type === 'success' ? 'text-emerald-400 font-semibold' :
                                log.type === 'agent' ? 'text-purple-400' : 'text-zinc-400'
                            }`}>
                                <span className="opacity-50 select-none">{log.type === 'user' ? '>' : '$'}</span> {log.text}
                            </div>
                        ))}
                        {status === 'processing' && <div className="animate-pulse text-indigo-400/50 mt-1">█</div>}
                    </div>

                    {/* Right Panel: Sardis Policy Engine */}
                    <div className="bg-zinc-900/50 p-4 rounded-xl border border-white/5 h-64 overflow-y-auto shadow-inner">
                        <div className="text-zinc-600 text-[10px] uppercase tracking-widest mb-3 border-b border-white/5 pb-2">
                            SARDIS POLICY ENGINE (CFO)
                        </div>
                        {dashboardLogs.length === 0 && <div className="text-zinc-700 italic">Awaiting transaction request...</div>}
                        {dashboardLogs.map((log, i) => (
                            <motion.div
                                initial={{ opacity: 0, x: -5 }}
                                animate={{ opacity: 1, x: 0 }}
                                key={i}
                                className={`mb-1.5 leading-relaxed ${log.color || 'text-zinc-300'}`}
                            >
                                <span className="text-zinc-700 text-[10px] select-none">[{new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span> {log.text}
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Background Glow Effect */}
            <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none group-hover:bg-indigo-500/20 transition-colors duration-700" />
        </div>
    );
};

export default SardisPlayground;
