/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sardis: {
          50: 'rgb(240 253 244 / <alpha-value>)',
          100: 'rgb(220 252 231 / <alpha-value>)',
          200: 'rgb(187 247 208 / <alpha-value>)',
          300: 'rgb(134 239 172 / <alpha-value>)',
          400: 'rgb(74 222 128 / <alpha-value>)',
          500: 'rgb(34 197 94 / <alpha-value>)',
          600: 'rgb(22 163 74 / <alpha-value>)',
          700: 'rgb(21 128 61 / <alpha-value>)',
          800: 'rgb(22 101 52 / <alpha-value>)',
          900: 'rgb(20 83 45 / <alpha-value>)',
          950: 'rgb(5 46 22 / <alpha-value>)',
        },
        dark: {
          100: 'rgb(30 41 59 / <alpha-value>)',
          200: 'rgb(26 35 50 / <alpha-value>)',
          300: 'rgb(21 29 41 / <alpha-value>)',
          400: 'rgb(17 24 39 / <alpha-value>)',
          500: 'rgb(15 23 42 / <alpha-value>)',
          600: 'rgb(12 18 34 / <alpha-value>)',
          700: 'rgb(9 13 24 / <alpha-value>)',
          800: 'rgb(6 9 16 / <alpha-value>)',
          900: 'rgb(3 4 8 / <alpha-value>)',
        }
      },
      fontFamily: {
        sans: ['JetBrains Mono', 'Menlo', 'monospace'],
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px #22c55e, 0 0 10px #22c55e, 0 0 15px #22c55e' },
          '100%': { boxShadow: '0 0 10px #22c55e, 0 0 20px #22c55e, 0 0 30px #22c55e' },
        }
      }
    },
  },
  plugins: [],
}
