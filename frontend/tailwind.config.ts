import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#FAF9F5",
          warm: "#F4F2EB",
          card: "#FFFFFF",
        },
        surface: "#FFFFFF",
        subtle: "#F3F2EC",
        earth: {
          sand: "#E5E3D8",
          amber: "#D97706",
          amberText: "#92400E",
        },
        botanical: {
          leaf: "#2E7D32",
        },
        border: {
          subtle: "#E5E3D8",
          DEFAULT: "#E5E3D8",
        },
        ink: {
          primary: "#191A15",
          secondary: "#5E6056",
          muted: "#8C8E84",
        },
        mastery: {
          emerald: "#2E7D32",
          emeraldLight: "#EDF7EE",
          emeraldText: "#1B5E20",
          amber: "#D97706",
          amberLight: "#FEF8E7",
          amberText: "#92400E",
          crimson: "#DC2626",
          crimsonLight: "#FDF2F2",
          crimsonText: "#991B1B",
          slate: "#64748B",
          slateLight: "#F3F4F6",
        },
      },
      fontFamily: {
        serif: ["var(--font-fraunces)", "serif"],
        sans: ["var(--font-jakarta)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
      },
      boxShadow: {
        subtle: "0 1px 3px rgba(25, 26, 21, 0.04)",
        card: "0 1px 3px rgba(25, 26, 21, 0.05), 0 1px 2px rgba(25, 26, 21, 0.03)",
        flyout: "0 4px 16px rgba(25, 26, 21, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
