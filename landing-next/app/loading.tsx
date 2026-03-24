export default function Loading() {
  return (
    <div
      className="min-h-[60vh] flex items-center justify-center"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      <div className="flex flex-col items-center gap-4">
        <div
          className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: "var(--landing-border)", borderTopColor: "transparent" }}
        />
        <span
          className="text-[13px]"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            color: "var(--landing-text-ghost)",
          }}
        >
          Loading...
        </span>
      </div>
    </div>
  );
}
