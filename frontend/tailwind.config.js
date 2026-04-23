/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
    './public/index.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        syne: ['Syne', 'sans-serif'],
        sans: ['DM Sans', 'sans-serif'],
      },
      colors: {
        primary: '#6c63ff',
        accent: '#38bdf8',
        green: '#34d399',
        amber: '#fbbf24',
        red: '#f87171',
        bg1: '#0a0a0f',
        bg2: '#0f0f18',
        bg3: '#12121a',
        bg4: '#1c1c28',
        glass: 'rgba(255,255,255,0.08)',
      },
      borderRadius: {
        card: '16px',
        input: '10px',
        pill: '100px',
      },
      boxShadow: {
        glow: '0 0 16px 0 #6c63ff55',
        glass: '0 4px 32px 0 rgba(108,99,255,0.08)',
      },
      keyframes: {
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%, 60%': { transform: 'translateX(-4px)' },
          '40%, 80%': { transform: 'translateX(4px)' },
        },
        flash: {
          '0%': { transform: 'scale(1)', background: '#34d399' },
          '50%': { transform: 'scale(1.02)', background: '#34d399' },
          '100%': { transform: 'scale(1)', background: 'inherit' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-400px 0' },
          '100%': { backgroundPosition: '400px 0' },
        },
      },
      animation: {
        shake: 'shake 0.4s cubic-bezier(0.34,1.56,0.64,1)',
        flash: 'flash 0.3s',
        shimmer: 'shimmer 1.2s linear infinite',
      },
    },
  },
  plugins: [],
};