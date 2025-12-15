/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        copper: {
          50: "#fff6f1",
          100: "#ffe8db",
          200: "#fdd0b4",
          300: "#fbb182",
          400: "#f27f3f",
          500: "#e25f1a",
          600: "#c74d13",
          700: "#a23c13",
          800: "#823215",
          900: "#6b2a14",
        },
      },
    },
  },
  plugins: [],
};
