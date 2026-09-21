import { useEffect, useState } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import ThemePicker from "../components/ThemePicker";

export default function Layout() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");

  useEffect(() => {
    api.auth.me().then((u) => setUsername(u.login)).catch(() => {});
  }, []);

  async function handleLogout() {
    await api.auth.logout().catch(() => {});
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-page text-text-base">
      <nav className="bg-nav border-b border-border-theme px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-primary text-lg">Каталог</span>
          <Link to="/" className="text-sm text-text-base hover:text-primary">Каталог</Link>
          <Link to="/stats" className="text-sm text-text-base hover:text-primary">Статистика</Link>
        </div>
        <div className="flex items-center gap-4">
          <ThemePicker />
          {username && <span className="text-sm text-muted">{username}</span>}
          <button onClick={handleLogout} className="text-sm text-muted hover:text-primary">
            Выйти
          </button>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
