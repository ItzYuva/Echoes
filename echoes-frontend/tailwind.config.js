/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        echoes: {
          bg: '#0D0D0D',
          'bg-secondary': '#141414',
          'bg-tertiary': '#1A1A1A',
          text: '#E8E4DF',
          'text-secondary': '#999999',
          'text-tertiary': '#555555',
          'accent-warm': '#E8A87C',
          'accent-cool': '#85CDCA',
          border: '#222222',
          'confidence-high': '#44AA99',
          'confidence-medium': '#DDAA33',
          'confidence-low': '#EE8855',
          'confidence-insufficient': '#EE5555',
        },
      },
      fontFamily: {
        story: ["'Source Serif 4'", "'Lora'", 'Georgia', 'serif'],
        ui: ["'Inter'", '-apple-system', 'sans-serif'],
        meta: ["'JetBrains Mono'", "'Fira Code'", 'monospace'],
      },
      fontSize: {
        'xs': '0.75rem',
        'sm': '0.875rem',
        'base': '1rem',
        'lg': '1.125rem',
        'xl': '1.5rem',
        '2xl': '2rem',
      },
      transitionDuration: {
        'fast': '150ms',
        'base': '300ms',
        'slow': '500ms',
      },
    },
  },
  plugins: [],
};
