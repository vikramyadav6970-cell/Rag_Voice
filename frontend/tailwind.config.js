/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0B0F14',
          900: '#10161F',
          850: '#141C27',
          800: '#182230',
        },
        brass: {
          400: '#DBB434',
          500: '#C9A227',
          600: '#A6841E',
        },
        teal: {
          400: '#72C0BE',
          500: '#3E8E8C',
          600: '#2E6E6C',
        },
        coral: {
          400: '#E57364',
          500: '#D65A4A',
          600: '#B84537',
        },
        offwhite: '#EDEAE3',
      },
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['IBM Plex Sans', 'IBM Plex Sans Devanagari', 'Noto Sans Tamil', '-apple-system', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Cascadia Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
