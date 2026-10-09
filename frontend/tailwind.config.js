/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        tev: {
          green: '#3b8d7f',
          darkgreen: '#286a5f',
          lightgreen: '#eaf5f3',
          gray: '#7a7b7f',
          darkgray: '#374151',
          lightgray: '#f3f4f6'
        }
      }
    },
  },
  plugins: [],
}
