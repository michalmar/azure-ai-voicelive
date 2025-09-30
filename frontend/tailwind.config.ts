import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", ...fontFamily.sans],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
      },
      keyframes: {
        pulseGlow: {
          "0%": { boxShadow: "0 0 20px rgba(56, 189, 248, 0.35)" },
          "50%": { boxShadow: "0 0 40px rgba(56, 189, 248, 0.6)" },
          "100%": { boxShadow: "0 0 20px rgba(56, 189, 248, 0.35)" },
        },
        spinSlow: {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
      },
      animation: {
        pulseGlow: "pulseGlow 6s ease-in-out infinite",
        spinSlow: "spinSlow 12s linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
