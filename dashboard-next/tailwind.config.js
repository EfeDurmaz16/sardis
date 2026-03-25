/** @type {import("tailwindcss").Config} */

const config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        sardis: {
          50: "rgb(255 247 237 / <alpha-value>)",
          100: "rgb(255 237 213 / <alpha-value>)",
          200: "rgb(255 213 173 / <alpha-value>)",
          300: "rgb(255 169 107 / <alpha-value>)",
          400: "rgb(255 106 42 / <alpha-value>)",
          500: "rgb(255 79 0 / <alpha-value>)",
          600: "rgb(221 62 0 / <alpha-value>)",
          700: "rgb(180 47 0 / <alpha-value>)",
          800: "rgb(140 38 0 / <alpha-value>)",
          900: "rgb(112 32 0 / <alpha-value>)",
          950: "rgb(64 16 0 / <alpha-value>)",
        },
        dark: {
          100: "#1f1f28",
          200: "#1c1c24",
          300: "#141419",
          400: "#0a0a0f",
          500: "#080810",
          600: "#060608",
          700: "#040406",
          800: "#020204",
          900: "#010102",
        },
        mono: {
          bg: "#09090b",
          surface: "#131316",
          elevated: "#1a1a1f",
          highest: "#222228",
          border: "#1f1f28",
          "border-hover": "#2a2a36",
          "border-strong": "#3a3a48",
          text: "#ececee",
          secondary: "#a0a0aa",
          muted: "#71717a",
          ghost: "#52525b",
          faint: "#3a3a44",
          accent: "#ff4f00",
        },
      },
      fontFamily: {
        sans: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "monospace"],
        display: ["Space Grotesk", "system-ui", "sans-serif"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        glow: "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        glow: {
          "0%": {
            boxShadow: "0 0 5px #ff4f00, 0 0 10px #ff4f00, 0 0 15px #ff4f00",
          },
          "100%": {
            boxShadow:
              "0 0 10px #ff4f00, 0 0 20px #ff4f00, 0 0 30px #ff4f00",
          },
        },
      },
    },
  },
  plugins: [],
};

module.exports = config;
