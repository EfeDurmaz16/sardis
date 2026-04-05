import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const alt = "Sardis — Safe payments for AI agents";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0A0A0A",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "24px",
          }}
        >
          <svg width="64" height="64" viewBox="0 0 28 28" fill="none">
            <path
              d="M20 5H10a7 7 0 000 14h2"
              stroke="white"
              strokeWidth="3"
              strokeLinecap="round"
              fill="none"
            />
            <path
              d="M8 23h10a7 7 0 000-14h-2"
              stroke="white"
              strokeWidth="3"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <h1
              style={{
                fontSize: "56px",
                fontWeight: 800,
                color: "white",
                letterSpacing: "-0.04em",
                margin: 0,
                lineHeight: 1.1,
                textAlign: "center",
              }}
            >
              Safe payments
              <br />
              for AI agents.
            </h1>
            <p
              style={{
                fontSize: "20px",
                color: "rgba(255,255,255,0.5)",
                margin: 0,
                textAlign: "center",
                maxWidth: "600px",
              }}
            >
              Set spending rules, enforce compliance guardrails, and let your
              agents transact autonomously.
            </p>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginTop: "8px",
            }}
          >
            <div
              style={{
                fontSize: "14px",
                fontWeight: 600,
                color: "rgba(255,255,255,0.3)",
                letterSpacing: "0.08em",
                textTransform: "uppercase" as const,
              }}
            >
              sardis.sh
            </div>
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
