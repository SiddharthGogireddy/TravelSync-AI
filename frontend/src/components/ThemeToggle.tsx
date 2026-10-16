import React from "react";
import { Sun, Moon, Laptop } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

export const ThemeToggle: React.FC = () => {
  const { theme, setTheme, resolvedTheme } = useTheme();

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        background: "var(--toggle-bg, #f1f5f9)",
        border: "1px solid var(--border, #cbd5e1)",
        borderRadius: "20px",
        padding: "2px",
        gap: "2px",
      }}
      role="group"
      aria-label="Theme selector"
    >
      <button
        type="button"
        onClick={() => setTheme("light")}
        title="Light theme"
        aria-label="Light theme"
        aria-pressed={theme === "light"}
        style={{
          background: theme === "light" ? "var(--card-bg, #ffffff)" : "transparent",
          color: theme === "light" ? "var(--accent, #4f46e5)" : "var(--text-muted, #64748b)",
          border: "none",
          borderRadius: "50%",
          width: "28px",
          height: "28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: theme === "light" ? "0 1px 3px rgba(0,0,0,0.15)" : "none",
          transition: "all 0.15s ease",
        }}
      >
        <Sun size={15} />
      </button>

      <button
        type="button"
        onClick={() => setTheme("dark")}
        title="Dark theme"
        aria-label="Dark theme"
        aria-pressed={theme === "dark"}
        style={{
          background: theme === "dark" ? "var(--card-bg, #1e293b)" : "transparent",
          color: theme === "dark" ? "var(--accent, #818cf8)" : "var(--text-muted, #64748b)",
          border: "none",
          borderRadius: "50%",
          width: "28px",
          height: "28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: theme === "dark" ? "0 1px 3px rgba(0,0,0,0.3)" : "none",
          transition: "all 0.15s ease",
        }}
      >
        <Moon size={15} />
      </button>

      <button
        type="button"
        onClick={() => setTheme("system")}
        title={`Follow system (${resolvedTheme})`}
        aria-label="Follow system theme"
        aria-pressed={theme === "system"}
        style={{
          background: theme === "system" ? "var(--card-bg, #ffffff)" : "transparent",
          color: theme === "system" ? "var(--accent, #4f46e5)" : "var(--text-muted, #64748b)",
          border: "none",
          borderRadius: "50%",
          width: "28px",
          height: "28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          boxShadow: theme === "system" ? "0 1px 3px rgba(0,0,0,0.15)" : "none",
          transition: "all 0.15s ease",
        }}
      >
        <Laptop size={15} />
      </button>
    </div>
  );
};

export default ThemeToggle;
