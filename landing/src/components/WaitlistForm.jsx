import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const WaitlistForm = ({
    ctaLabel = 'GET ACCESS',
    successTitle = "You're on the list",
    successDescription = "You've been registered for Sardis. We'll reach out soon with your access credentials.",
}) => {
    const [email, setEmail] = useState('');
    const [status, setStatus] = useState('idle'); // idle, loading, success, error
    const [errorMessage, setErrorMessage] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus('loading');
        setErrorMessage('');

        // Basic email validation
        if (!email || !email.includes('@')) {
            setStatus('error');
            setErrorMessage('Please enter a valid email address.');
            return;
        }

        try {
            const response = await fetch('/api/waitlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });

            const data = await response.json();

            if (response.status === 409) {
                setStatus('error');
                setErrorMessage('This email is already on the waitlist.');
                return;
            }

            if (!response.ok) {
                throw new Error(data.error || 'Failed to join waitlist');
            }

            setStatus('success');
        } catch (error) {
            setStatus('error');
            setErrorMessage(error.message || 'Something went wrong. Please try again.');
        }
    };

    if (status === 'success') {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center p-6 bg-emerald-500/10 border border-emerald-500/30"
            >
                <div className="w-12 h-12 bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center mx-auto mb-4 font-mono font-bold text-emerald-500">
                    OK
                </div>
                <h3 className="text-lg font-bold text-emerald-500 mb-2 font-display">{successTitle}</h3>
                <p className="text-muted-foreground text-sm font-mono">{successDescription}</p>
            </motion.div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <div className="flex-1 relative">
                <input
                    type="text"
                    inputMode="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full h-12 px-4 bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-[var(--sardis-orange)] transition-colors font-mono"
                    disabled={status === 'loading'}
                />
                <AnimatePresence>
                    {status === 'error' && (
                        <motion.p
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="absolute -bottom-6 left-0 text-xs text-red-500 font-mono"
                        >
                            {errorMessage}
                        </motion.p>
                    )}
                </AnimatePresence>
            </div>
            <button
                type="submit"
                disabled={status === 'loading'}
                className="h-12 px-6 bg-[var(--sardis-orange)] text-white font-semibold hover:bg-[var(--sardis-orange)]/90 transition-colors disabled:opacity-70 flex items-center justify-center gap-2 font-mono"
            >
                {status === 'loading' ? (
                    <>
                        <span className="animate-pulse">...</span>
                        JOINING
                    </>
                ) : (
                    <>
                        {ctaLabel}
                        <span>→</span>
                    </>
                )}
            </button>
        </form>
    );
};

export default WaitlistForm;
