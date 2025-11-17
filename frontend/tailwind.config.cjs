module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx,jsx,js}"],
  theme: {
    extend: {
      colors: {
        'forest-green': '#0F3D2E',
        'pine-deep': '#0A2A20',
        'pine-mid': '#155B42',
        'sage-light': '#F2F5EE',
        'sage-mid': '#DDE3D5',
        'earth-brown': '#7B4F2A',
        'terracotta': '#B5543A',
        'accent-gold': '#C9A227',
        'error-red': '#B33636'
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'Arial', 'sans-serif']
      },
      keyframes: {
        'slide-in': {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' }
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' }
        }
      },
      animation: {
        'slide-in': 'slide-in 0.3s ease-out',
        'fade-in': 'fade-in 0.2s ease-in',
        'pulse-slow': 'pulse-slow 2s ease-in-out infinite'
      }
    }
  },
  plugins: []
};
