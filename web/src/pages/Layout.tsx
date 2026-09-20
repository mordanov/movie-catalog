import { Link, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Layout() {
  const navigate = useNavigate();

  async function handleLogout() {
    await api.auth.logout().catch(() => {});
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-indigo-600 text-lg">Каталог</span>
          <Link to="/" className="text-sm text-gray-700 hover:text-indigo-600">Каталог</Link>
          <Link to="/stats" className="text-sm text-gray-700 hover:text-indigo-600">Статистика</Link>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-red-600"
        >
          Выйти
        </button>
      </nav>
      <main className="max-w-7xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
