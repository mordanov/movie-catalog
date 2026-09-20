import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import Login from "./pages/Login";
import Layout from "./pages/Layout";

// Lazy imports (created in Tasks 11-12)
const Catalog = lazy(() => import("./pages/Catalog"));
const Stats = lazy(() => import("./pages/Stats"));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<"loading" | "ok" | "fail">("loading");

  useEffect(() => {
    api.auth.me().then(() => setAuth("ok")).catch(() => setAuth("fail"));
  }, []);

  if (auth === "loading") return <div className="p-4 text-gray-500">Загрузка...</div>;
  if (auth === "fail") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <Suspense fallback={<div>Загрузка...</div>}>
                <Catalog />
              </Suspense>
            }
          />
          <Route
            path="stats"
            element={
              <Suspense fallback={<div>Загрузка...</div>}>
                <Stats />
              </Suspense>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
