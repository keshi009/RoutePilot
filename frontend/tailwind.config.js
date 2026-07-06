/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 18px 45px rgba(24, 37, 68, 0.12)",
      },
    },
  },
  plugins: [],
};
