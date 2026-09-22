import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import ThemePicker from "../components/ThemePicker";
import BottomNav from "../components/BottomNav";
import AddMediaModal from "../components/AddMediaModal";

export interface CatalogOutletContext {
  addedCount: number;
  onAdd: () => void;
}

export default function Layout() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [addedCount, setAddedCount] = useState(0);

  useEffect(() => {
    api.auth.me().then((u) => setUsername(u.login)).catch(() => {});
  }, []);

  async function handleLogout() {
    await api.auth.logout().catch(() => {});
    navigate("/login");
  }

  function handleAdded() {
    setShowAdd(false);
    setAddedCount((c) => c + 1);
  }

  return (
    <div className="min-h-screen bg-page text-text-base">
      {/* Top nav */}
      <nav className="bg-nav border-b border-border-theme px-4 py-3 flex items-center justify-between">
        {/* Desktop: logo + links */}
        <div className="flex items-center gap-6">
          <span className="font-bold text-primary text-lg">Каталог</span>
          <Link to="/" className="hidden md:inline text-sm text-text-base hover:text-primary">Каталог</Link>
          <Link to="/stats" className="hidden md:inline text-sm text-text-base hover:text-primary">Статистика</Link>
        </div>
        {/* Right side */}
        <div className="flex items-center gap-4">
          <ThemePicker />
          {username && <span className="hidden md:inline text-sm text-muted">{username}</span>}
          <button onClick={handleLogout} className="hidden md:inline text-sm text-muted hover:text-primary">
            Выйти
          </button>
        </div>
      </nav>

      {/* Main content — pb-24 on mobile to clear the bottom nav */}
      <main className="max-w-7xl mx-auto px-4 py-6 pb-24 md:pb-6">
        <Outlet context={{ addedCount, onAdd: () => setShowAdd(true) } satisfies CatalogOutletContext} />
      </main>

      {/* Mobile bottom nav */}
      <BottomNav onAdd={() => setShowAdd(true)} />

      {showAdd && (
        <AddMediaModal onClose={() => setShowAdd(false)} onAdded={handleAdded} />
      )}
    </div>
  );
}
