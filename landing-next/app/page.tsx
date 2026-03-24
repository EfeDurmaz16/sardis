import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sardis: The Payment OS for the Agent Economy",
  description:
    "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust. Non-custodial wallets, spending policies, on-chain payments on Base with multi-chain funding.",
};

export default function HomePage() {
  return (
    <main
      id="main-content"
      className="min-h-screen"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      {/* Placeholder — will be replaced with full home page */}
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-20">
        <h1
          className="font-bold tracking-[-0.04em] mb-6"
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            fontSize: "clamp(36px, 5vw, 64px)",
            color: "var(--landing-text-primary)",
          }}
        >
          The Payment OS for the Agent Economy
        </h1>
      </div>
    </main>
  );
}
