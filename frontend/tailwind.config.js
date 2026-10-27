/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        charcoal: { 50: "#f5f5f6", 100: "#e6e7e9", 200: "#cfd1d5", 400: "#80848c", 500: "#5b5f68", 600: "#3f434b", 700: "#2d3036", 800: "#23262b", 900: "#1a1c20", 950: "#121316" },
        warm: { 50: "#fdfbf7", 100: "#faf7f2", 200: "#f2ece1", 300: "#e6dccb" },
        gold: { 300: "#e0c78f", 400: "#d0ac5e", 500: "#b8913f", 600: "#9a7630", 700: "#7c5e26" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        serif: ["Playfair Display", "Georgia", "Cambria", "serif"],
      },
      boxShadow: { card: "0 1px 2px rgba(26,28,32,.05), 0 8px 24px -12px rgba(26,28,32,.18)" },
    },
  },
  plugins: [],
};
