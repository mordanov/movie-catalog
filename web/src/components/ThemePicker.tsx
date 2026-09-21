import { useTheme, type ThemeId } from "../hooks/useTheme";

const SWATCHES: Record<ThemeId, { bg: string; label: string }> = {
  light:    { bg: "#4f46e5", label: "Светлая" },
  dark:     { bg: "#e50914", label: "Тёмная" },
  midnight: { bg: "#3b82f6", label: "Полночь" },
  warm:     { bg: "#d97706", label: "Тёплая" },
  emerald:  { bg: "#10b981", label: "Изумруд" },
};

export default function ThemePicker() {
  const { theme, setTheme, themes } = useTheme();
  return (
    <div className="flex items-center gap-1.5" role="group" aria-label="Цветовая схема">
      {themes.map((t) => (
        <button
          key={t}
          title={SWATCHES[t].label}
          onClick={() => setTheme(t)}
          className={`w-5 h-5 rounded-full border-2 transition-transform ${
            theme === t ? "border-text-base scale-125" : "border-transparent hover:scale-110"
          }`}
          style={{ backgroundColor: SWATCHES[t].bg }}
          aria-pressed={theme === t}
        />
      ))}
    </div>
  );
}
