"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Sun, Moon } from "lucide-react";
import Link from "next/link";

const navLinks = [
  { label: "Docs", href: "/docs" },
  { label: "Quickstart", href: "https://docs.sardis.sh/docs/quickstart" },
  { label: "Pricing", href: "/pricing" },
  { label: "GitHub", href: "https://github.com/EfeDurmaz16/sardis" },
  { label: "Blog", href: "/docs/blog" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    if (stored) {
      setDarkMode(stored === "dark");
    } else {
      setDarkMode(document.documentElement.classList.contains("dark"));
    }
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [darkMode]);

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  return (
    <>
      <nav
        aria-label="Main navigation"
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled ? "backdrop-blur-md border-b" : "bg-transparent"
        }`}
        style={
          scrolled
            ? {
                backgroundColor:
                  "color-mix(in srgb, var(--landing-bg) 80%, transparent)",
                borderBottomColor: "var(--landing-border)",
              }
            : undefined
        }
      >
        <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
              <svg
                width="34"
                height="34"
                viewBox="0 0 28 28"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M20 5H10a7 7 0 000 14h2"
                  stroke="var(--landing-text-primary)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M8 23h10a7 7 0 000-14h-2"
                  stroke="var(--landing-text-primary)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>
              <span
                className="text-2xl font-bold leading-none"
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  color: "var(--landing-text-primary)",
                }}
              >
                Sardis
              </span>
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-8">
              {navLinks.map((link) =>
                link.href.startsWith("http") ? (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[14px] transition-colors duration-200 hover:text-[var(--landing-text-secondary)]"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      color: "var(--landing-text-muted)",
                    }}
                  >
                    {link.label}
                  </a>
                ) : (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="text-[14px] transition-colors duration-200 hover:text-[var(--landing-text-secondary)]"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      color: "var(--landing-text-muted)",
                    }}
                  >
                    {link.label}
                  </Link>
                )
              )}

              {/* Theme toggle */}
              <button
                onClick={() => setDarkMode((prev) => !prev)}
                className="p-2 rounded-lg transition-colors duration-200"
                style={{ color: "var(--landing-text-muted)" }}
                aria-label={
                  darkMode ? "Switch to light mode" : "Switch to dark mode"
                }
              >
                {darkMode ? <Sun size={18} /> : <Moon size={18} />}
              </button>

              <a
                href="https://dashboard.sardis.sh/signup"
                className="text-[14px] font-medium text-white rounded-lg transition-colors duration-200 px-4 py-2 inline-block hover:opacity-90"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  backgroundColor: "var(--landing-accent)",
                }}
              >
                Get Started Free
              </a>
            </div>

            {/* Mobile hamburger */}
            <button
              className="md:hidden transition-colors duration-200 p-1"
              style={{ color: "var(--landing-text-muted)" }}
              onClick={() => setMobileOpen((prev) => !prev)}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
            >
              {mobileOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile full-screen overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            key="mobile-menu"
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed inset-0 z-40 flex flex-col"
            style={{ backgroundColor: "var(--landing-bg)" }}
          >
            {/* Top bar */}
            <div className="flex items-center justify-between h-16 px-5">
              <Link
                href="/"
                className="flex items-center gap-2.5"
                onClick={() => setMobileOpen(false)}
              >
                <svg
                  width="34"
                  height="34"
                  viewBox="0 0 28 28"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M20 5H10a7 7 0 000 14h2"
                    stroke="var(--landing-text-primary)"
                    strokeWidth="3"
                    strokeLinecap="round"
                    fill="none"
                  />
                  <path
                    d="M8 23h10a7 7 0 000-14h-2"
                    stroke="var(--landing-text-primary)"
                    strokeWidth="3"
                    strokeLinecap="round"
                    fill="none"
                  />
                </svg>
                <span
                  className="text-2xl font-bold leading-none"
                  style={{
                    fontFamily: "'Space Grotesk', sans-serif",
                    color: "var(--landing-text-primary)",
                  }}
                >
                  Sardis
                </span>
              </Link>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setDarkMode((prev) => !prev)}
                  className="p-2 rounded-lg transition-colors duration-200"
                  style={{ color: "var(--landing-text-muted)" }}
                  aria-label={
                    darkMode ? "Switch to light mode" : "Switch to dark mode"
                  }
                >
                  {darkMode ? <Sun size={20} /> : <Moon size={20} />}
                </button>
                <button
                  className="transition-colors duration-200 p-1"
                  style={{ color: "var(--landing-text-muted)" }}
                  onClick={() => setMobileOpen(false)}
                  aria-label="Close menu"
                >
                  <X size={24} />
                </button>
              </div>
            </div>

            {/* Nav links */}
            <div className="flex flex-col items-start gap-6 px-5 pt-10">
              {navLinks.map((link, i) =>
                link.href.startsWith("http") ? (
                  <motion.a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 + i * 0.06, duration: 0.2 }}
                    className="text-[22px] transition-colors duration-200 font-medium"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      color: "var(--landing-text-muted)",
                    }}
                    onClick={() => setMobileOpen(false)}
                  >
                    {link.label}
                  </motion.a>
                ) : (
                  <motion.div
                    key={link.label}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 + i * 0.06, duration: 0.2 }}
                  >
                    <Link
                      href={link.href}
                      className="text-[22px] transition-colors duration-200 font-medium"
                      style={{
                        fontFamily: "'Inter', sans-serif",
                        color: "var(--landing-text-muted)",
                      }}
                      onClick={() => setMobileOpen(false)}
                    >
                      {link.label}
                    </Link>
                  </motion.div>
                )
              )}

              <motion.a
                href="https://dashboard.sardis.sh/signup"
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: 0.05 + navLinks.length * 0.06,
                  duration: 0.2,
                }}
                onClick={() => setMobileOpen(false)}
                className="mt-4 text-[16px] font-medium text-white rounded-lg transition-colors duration-200 px-6 py-3 w-full text-center inline-block"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  backgroundColor: "var(--landing-accent)",
                }}
              >
                Get Started Free
              </motion.a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
