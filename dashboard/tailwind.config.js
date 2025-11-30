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
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
          950: '#052e16',
        },
        dark: {
          100: '#1e293b',
          200: '#1a2332',
          300: '#151d29',
          400: '#111827',
          500: '#0f172a',
          600: '#0c1222',
          700: '#090d18',
          800: '#060910',
          900: '#030408',
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

