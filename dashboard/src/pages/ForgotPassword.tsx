import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Key } from '@phosphor-icons/react';
const API_URL = import.meta.env.VITE_API_URL || '';

export default function ForgotPassword() {
    const [email, setEmail] = useState('');
    const [submitted, setSubmitted] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            await fetch(`${API_URL}/api/v2/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.trim().toLowerCase() }),
            });
        } catch {
            // Always show success to prevent email enumeration
        } finally {
            setIsLoading(false);
            setSubmitted(true);
        }
    };

    if (submitted) {
        return (
            <div className="min-h-screen bg-dark-400 flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    <div className="text-center mb-8">
                        <div className="w-16 h-16 bg-green-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                            <CheckCircle className="w-8 h-8 text-green-400" />
                        </div>
                        <h1 className="text-3xl font-bold text-white font-display">Check Your Email</h1>
                        <p className="text-gray-400 mt-2">
                            If an account with <span className="text-white">{email}</span> exists,
                            we've sent a password reset link. It expires in 1 hour.
                        </p>
                    </div>

                    <div className="card p-8 text-center space-y-4">
                        <p className="text-sm text-gray-500">
                            Didn't receive the email? Check your spam folder or try again.
                        </p>
                        <button
                            onClick={() => setSubmitted(false)}
                            className="text-sardis-400 hover:text-sardis-300 text-sm transition-colors"
                        >
                            Try a different email
                        </button>
                        <div className="pt-2">
                            <Link to="/login" className="text-sm text-gray-500 hover:text-gray-400 transition-colors flex items-center justify-center gap-1">
                                <ArrowLeft className="w-4 h-4" /> Back to login
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-dark-400 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-sardis-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                        <Key className="w-8 h-8 text-sardis-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-white font-display">Reset Password</h1>
                    <p className="text-gray-400 mt-2">Enter your email to receive a reset link</p>
                </div>

                <div className="card p-8">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-400 mb-2">
                                Email Address
                            </label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full px-4 py-3 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50 transition-colors"
                                placeholder="you@company.com"
                                required
                                autoComplete="email"
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-3 bg-sardis-500 text-dark-400 font-bold rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? 'Sending...' : 'Send Reset Link'}
                        </button>
                    </form>

                    <div className="mt-6 text-center">
                        <Link to="/login" className="text-sm text-gray-500 hover:text-gray-400 transition-colors flex items-center justify-center gap-1">
                            <ArrowLeft className="w-4 h-4" /> Back to login
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
