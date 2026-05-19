/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,html}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#dbe6ff',
          200: '#b9cdff',
          300: '#8cabff',
          400: '#5e81ff',
          500: '#3776AB',
          600: '#2c5e89',
          700: '#23496a',
          800: '#1b394f',
          900: '#142a3a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(55,118,171,0.25), 0 20px 50px -20px rgba(55,118,171,0.45)',
      },
    },
  },
  plugins: [],
};
