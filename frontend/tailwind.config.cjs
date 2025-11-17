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
      }
    }
  },
  plugins: []
};
