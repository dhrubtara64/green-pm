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
        "gpm-green": "#16a34a",
        "gpm-dark": "#0f172a",
        "gpm-slate": "#1e293b",
        "gpm-border": "#334155",
        "gpm-muted": "#94a3b8",
      },
    },
  },
  plugins: [],
};

export default config;
