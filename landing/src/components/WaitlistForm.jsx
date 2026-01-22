import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ArrowRight, Spinner } from '@phosphor-icons/react';

const WaitlistForm = () => {
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
            // For now, simulate API call with localStorage fallback
            // In production, replace with actual API endpoint:
            // const response = await fetch('/api/waitlist', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ email })
            // });

            await new Promise(resolve => setTimeout(resolve, 1000));

            // Store in localStorage for demo purposes
            const existingEmails = JSON.parse(localStorage.getItem('sardis_waitlist') || '[]');
            if (existingEmails.includes(email)) {
                setStatus('error');
                setErrorMessage('This email is already on the waitlist.');
                return;
            }
            existingEmails.push(email);
            localStorage.setItem('sardis_waitlist', JSON.stringify(existingEmails));

            setStatus('success');
        } catch (error) {
            setStatus('error');
            setErrorMessage('Something went wrong. Please try again.');
        }
    };

    if (status === 'success') {
        return (
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center p-6 rounded-xl bg-emerald-500/10 border border-emerald-500/20"
            >
                <div className="w-12 h-12 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Check weight="bold" className="text-emerald-400" size={24} />
                </div>
                <h3 className="text-lg font-bold text-emerald-400 mb-2">You're on the list!</h3>
                <p className="text-zinc-400 text-sm">
                    You've been added to the Alpha Design Partner program waitlist. We'll reach out soon with early access.
                </p>
            </motion.div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
            <div className="flex-1 relative">
                <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="w-full h-12 px-4 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all"
                    disabled={status === 'loading'}
                />
                <AnimatePresence>
                    {status === 'error' && (
                        <motion.p
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="absolute -bottom-6 left-0 text-xs text-red-400"
                        >
                            {errorMessage}
                        </motion.p>
                    )}
                </AnimatePresence>
            </div>
            <button
                type="submit"
                disabled={status === 'loading'}
                className="h-12 px-6 rounded-lg bg-white text-black font-semibold hover:bg-zinc-200 transition-all disabled:opacity-70 flex items-center justify-center gap-2"
            >
                {status === 'loading' ? (
                    <>
                        <Spinner className="animate-spin" size={18} />
                        Joining...
                    </>
                ) : (
                    <>
                        Join Waitlist
                        <ArrowRight weight="bold" size={16} />
                    </>
                )}
            </button>
        </form>
    );
};

export default WaitlistForm;
