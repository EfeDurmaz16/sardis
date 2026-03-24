import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "404 - Page Not Found",
  description: "The page you are looking for does not exist.",
};

export default function NotFound() {
  return (
    <main
      className="min-h-[70vh] flex flex-col items-center justify-center text-center px-5"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      <h1
        className="text-[72px] font-bold tracking-[-0.04em] mb-4"
        style={{
          fontFamily: "'Space Grotesk', sans-serif",
          color: "var(--landing-text-primary)",
        }}
      >
        404
      </h1>
      <p
        className="text-[16px] mb-8"
        style={{
          fontFamily: "'Inter', sans-serif",
          color: "var(--landing-text-tertiary)",
        }}
      >
        The page you are looking for does not exist.
      </p>
      <Link
        href="/"
        className="text-white rounded-lg py-3 px-8 transition-colors text-[15px] font-medium inline-block"
        style={{ backgroundColor: "var(--landing-accent)" }}
      >
        Go Home
      </Link>
    </main>
  );
}
