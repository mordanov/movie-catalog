import { useState, useEffect } from "react";

const THEMES = ["light", "dark", "midnight", "warm", "emerald"] as const;
export type ThemeId = (typeof THEMES)[number];
const KEY = "catalog_theme";

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeId>(() => {
    try {
      const stored = localStorage.getItem(KEY);
      return (THEMES.includes(stored as ThemeId) ? stored : "light") as ThemeId;
    } catch {
      return "light";
    }
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
  }, [theme]);

  // Apply on mount (handles SSR/initial paint)
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, []);

  return { theme, setTheme: setThemeState, themes: THEMES };
}
