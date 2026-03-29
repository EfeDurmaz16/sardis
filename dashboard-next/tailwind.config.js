/** @type {import("tailwindcss").Config} */

const config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        /* shadcn/ui CSS variable colors */
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground, #ffffff)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        sidebar: {
          DEFAULT: "var(--sidebar)",
          foreground: "var(--sidebar-foreground)",
          primary: "var(--sidebar-primary)",
          "primary-foreground": "var(--sidebar-primary-foreground)",
          accent: "var(--sidebar-accent)",
          "accent-foreground": "var(--sidebar-accent-foreground)",
          border: "var(--sidebar-border)",
          ring: "var(--sidebar-ring)",
        },
        chart: {
          1: "var(--chart-1)",
          2: "var(--chart-2)",
          3: "var(--chart-3)",
          4: "var(--chart-4)",
          5: "var(--chart-5)",
        },

        /* Sardis brand */
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
        /* Remapped dark scale → light values */
        dark: {
          100: "#eaeaea",
          200: "#f2f2f2",
          300: "#ffffff",
          400: "#fafafa",
          500: "#fafafa",
          600: "#f7f7f7",
          700: "#f2f2f2",
          800: "#ebebeb",
          900: "#e0e0e0",
        },
        /* Mono palette → light equivalents */
        mono: {
          bg: "#fafafa",
          surface: "#ffffff",
          elevated: "#f7f7f7",
          highest: "#f2f2f2",
          border: "#eaeaea",
          "border-hover": "#d0d0d0",
          "border-strong": "#bbbbbb",
          text: "#111111",
          secondary: "#666666",
          muted: "#888888",
          ghost: "#bbbbbb",
          faint: "#d0d0d0",
          accent: "#111111",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
        display: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "7px",
        md: "7px",
        lg: "var(--radius)",
        xl: "12px",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

module.exports = config;
