/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "var(--bg-page)",
        surface: "var(--bg-surface)",
        nav: "var(--bg-nav)",
        primary: "var(--color-primary)",
        "primary-hover": "var(--color-primary-hover)",
        "text-base": "var(--color-text)",
        muted: "var(--color-muted)",
        "border-theme": "var(--color-border)",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
