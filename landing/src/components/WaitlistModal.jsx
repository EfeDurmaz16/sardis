import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import SardisLogo from "./SardisLogo";

export default function WaitlistModal({ isOpen, onClose }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle, loading, success, error
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");

    // Basic email validation
    if (!email || !email.includes("@")) {
      setStatus("error");
      setErrorMessage("Please enter a valid email address.");
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
        setStatus("error");
        setErrorMessage("This email is already on the waitlist.");
        return;
      }

      if (!response.ok) {
        throw new Error(data.error || 'Failed to join waitlist');
      }

      setStatus("success");
    } catch (error) {
      setStatus("error");
      setErrorMessage(error.message || "Something went wrong. Please try again.");
    }
  };

  const handleClose = () => {
    setEmail("");
    setStatus("idle");
    setErrorMessage("");
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50"
          >
            <div className="bg-background border border-border p-8 relative">
              {/* Close button */}
              <button
                onClick={handleClose}
                className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center border border-border hover:border-[var(--sardis-orange)] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>

              {status === "success" ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center"
                >
                  <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto mb-6 font-mono font-bold text-emerald-500 text-xl">
                    OK
                  </div>
                  <h3 className="text-2xl font-bold text-emerald-500 mb-3 font-display">
                    You're on the list
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    You've been added to the Alpha Design Partner program
                    waitlist. We'll reach out soon with early access.
                  </p>
                  <Button
                    onClick={handleClose}
                    className="bg-emerald-500 hover:bg-emerald-600 text-white rounded-none"
                  >
                    Close
                  </Button>
                </motion.div>
              ) : (
                <>
                  {/* Header */}
                  <div className="text-center mb-6">
                    <SardisLogo className="mx-auto mb-4" size="large" />
                    <h2 className="text-2xl font-bold font-display mb-2">
                      Get Early Access
                    </h2>
                    <p className="text-muted-foreground">
                      Join the Alpha Design Partner program and be among the
                      first to give your agents financial autonomy.
                    </p>
                  </div>

                  {/* Form */}
                  <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                      <input
                        type="text"
                        inputMode="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@company.com"
                        className="w-full h-12 px-4 bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-[var(--sardis-orange)] transition-colors font-mono"
                        disabled={status === "loading"}
                      />
                      <AnimatePresence>
                        {status === "error" && (
                          <motion.p
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="mt-2 text-sm text-red-500 font-mono"
                          >
                            {errorMessage}
                          </motion.p>
                        )}
                      </AnimatePresence>
                    </div>

                    <Button
                      type="submit"
                      disabled={status === "loading"}
                      className="w-full h-12 bg-[var(--sardis-orange)] hover:bg-[var(--sardis-orange)]/90 text-white font-semibold rounded-none"
                    >
                      {status === "loading" ? (
                        <span className="flex items-center gap-2">
                          <span className="animate-pulse">...</span>
                          Joining
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          Join Waitlist
                          <span>→</span>
                        </span>
                      )}
                    </Button>
                  </form>

                  {/* Footer */}
                  <p className="text-xs text-muted-foreground text-center mt-4 font-mono">
                    No spam. We'll only contact you about Sardis updates.
                  </p>
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
