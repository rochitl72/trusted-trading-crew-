/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html","./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg0: "#070B14",
        bg1: "#0E1626",
        bg2: "#111b30",
        line: "#1b2b4a",
        ink: "#D7E3FF",
        accent: {
          1: "#19A7FF",
          2: "#7C4DFF",
          3: "#00E5A8",
          4: "#FF6B6B",
          5: "#FFC857"
        }
      },
      boxShadow: {
        glow: "0 0 40px rgba(25,167,255,0.18)",
        card: "0 10px 40px rgba(0,0,0,0.45)"
      },
      fontFamily: {
        sans: ["Inter","system-ui","Segoe UI","Roboto","Helvetica","Arial","sans-serif"],
        mono: ["JetBrains Mono","ui-monospace","SFMono-Regular","Menlo","Monaco","monospace"]
      }
    },
  },
  plugins: [],
}
