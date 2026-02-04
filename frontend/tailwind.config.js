/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Custom colors for alproj-gui (topographic minimal + icon blues)
        primary: {
          50: '#f2f7fb',
          100: '#e3eef8',
          200: '#c1ddf1',
          300: '#8fc5e6',
          400: '#58a9d8',
          500: '#2b8fc8',
          600: '#0b63a8', // Main alpine blue
          700: '#0a4f87',
          800: '#0c3f6b',
          900: '#0b3253',
          950: '#072033'
        },
        accent: {
          50: '#fff6f0',
          100: '#ffe8dc',
          200: '#ffd0b8',
          300: '#ffb088',
          400: '#ff8d5e',
          500: '#f17847',
          600: '#df5e2c',
          700: '#b74a22',
          800: '#933c1e',
          900: '#76331c',
          950: '#3d180d'
        }
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace']
      }
    }
  },
  plugins: [require('@tailwindcss/forms')]
};
