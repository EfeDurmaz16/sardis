/** @type {import("tailwindcss").Config} */

const config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        sardis: {
          50: "rgb(240 253 244 / <alpha-value>)",
          100: "rgb(220 252 231 / <alpha-value>)",
          200: "rgb(187 247 208 / <alpha-value>)",
          300: "rgb(134 239 172 / <alpha-value>)",
          400: "rgb(74 222 128 / <alpha-value>)",
          500: "rgb(34 197 94 / <alpha-value>)",
          600: "rgb(22 163 74 / <alpha-value>)",
          700: "rgb(21 128 61 / <alpha-value>)",
          800: "rgb(22 101 52 / <alpha-value>)",
          900: "rgb(20 83 45 / <alpha-value>)",
          950: "rgb(5 46 22 / <alpha-value>)",
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
          bg: "#0a0a0f",
          surface: "#141419",
          elevated: "#1c1c24",
          border: "#1f1f28",
          "border-hover": "#2a2a36",
          text: "#e4e4e7",
          muted: "#71717a",
          ghost: "#52525b",
          accent: "#22c55e",
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
            boxShadow: "0 0 5px #22c55e, 0 0 10px #22c55e, 0 0 15px #22c55e",
          },
          "100%": {
            boxShadow:
              "0 0 10px #22c55e, 0 0 20px #22c55e, 0 0 30px #22c55e",
          },
        },
      },
    },
  },
  plugins: [],
};

module.exports = config;
