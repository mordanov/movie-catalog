import { useLocation, useNavigate } from "react-router-dom";

interface Props {
  onAdd: () => void;
}

const TABS = [
  { label: "Каталог",    icon: "🎬", path: "/" },
  { label: "Статистика", icon: "📊", path: "/stats" },
] as const;

export default function BottomNav({ onAdd }: Props) {
  const location = useLocation();
  const navigate = useNavigate();

  const tabClass = (active: boolean) =>
    `flex-1 flex flex-col items-center py-2 gap-0.5 text-xs ${active ? "text-primary" : "text-muted hover:text-primary"}`;

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 bg-nav border-t border-border-theme md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex">
        {TABS.map((tab) => (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={tabClass(location.pathname === tab.path)}
          >
            <span className="text-xl leading-none">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
        <button onClick={onAdd} className={tabClass(false)}>
          <span className="text-xl leading-none font-bold">＋</span>
          <span>Добавить</span>
        </button>
      </div>
    </nav>
  );
}
