const { fontFamily } = require("tailwindcss/defaultTheme")

module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "rgb(var(--border))", // Changed from hsl
        input: "rgb(var(--input))", // Changed from hsl
        ring: "rgb(var(--ring))", // Changed from hsl
        background: "rgb(var(--background))", // Changed from hsl
        foreground: "rgb(var(--foreground))", // Changed from hsl
        primary: {
          DEFAULT: "rgb(var(--primary))", // Changed from hsl
          foreground: "rgb(var(--primary-foreground))", // Changed from hsl
        },
        secondary: {
          DEFAULT: "rgb(var(--secondary))", // Changed from hsl
          foreground: "rgb(var(--secondary-foreground))", // Changed from hsl
        },
        destructive: {
          DEFAULT: "rgb(var(--destructive))", // Changed from hsl
          foreground: "rgb(var(--destructive-foreground))", // Changed from hsl
        },
        muted: {
          DEFAULT: "rgb(var(--muted))", // Changed from hsl
          foreground: "rgb(var(--muted-foreground))", // Changed from hsl
        },
        accent: {
          DEFAULT: "rgb(var(--accent))", // Changed from hsl
          foreground: "rgb(var(--accent-foreground))", // Changed from hsl
        },
        popover: {
          DEFAULT: "rgb(var(--popover))", // Changed from hsl
          foreground: "rgb(var(--popover-foreground))", // Changed from hsl
        },
        card: {
          DEFAULT: "rgb(var(--card))", // Changed from hsl
          foreground: "rgb(var(--card-foreground))", // Changed from hsl
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      fontFamily: {
        outfit: ['Outfit', ...fontFamily.sans],
        manrope: ['Manrope', ...fontFamily.sans],
        mono: ['JetBrains Mono', ...fontFamily.mono],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}