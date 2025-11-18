import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary colors (slate) - Professional & trustworthy
        primary: {
          DEFAULT: "#334155", // slate-700
          light: "#475569",   // slate-600
          dark: "#1e293b",    // slate-800
        },

        // Secondary colors (teal) - Modern accent
        secondary: {
          DEFAULT: "#0f766e", // teal-700
          light: "#0d9488",   // teal-600
          dark: "#115e59",    // teal-800
        },

        // Accent color (amber) - Warmth and emphasis
        accent: {
          DEFAULT: "#f59e0b", // amber-500
          light: "#fbbf24",   // amber-400
          dark: "#d97706",    // amber-600
        },
      },
      fontFamily: {
        // System font stack - optimized for readability
        sans: [
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
          '"Apple Color Emoji"',
          '"Segoe UI Emoji"',
          '"Segoe UI Symbol"',
        ],
        // Monospace for citations and code
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          '"SF Mono"',
          "Menlo",
          "Monaco",
          "Consolas",
          '"Liberation Mono"',
          '"Courier New"',
          "monospace",
        ],
      },
      spacing: {
        // Additional spacing values for consistent layouts
        "18": "4.5rem",
        "88": "22rem",
      },
      maxWidth: {
        // Content width constraints
        "8xl": "88rem",
        "9xl": "96rem",
      },
    },
  },
  plugins: [],
};

export default config;
