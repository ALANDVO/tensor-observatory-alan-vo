import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { LoadingFullScreen } from './components/Loading';
import { ErrorState } from './components/ErrorState';
import { useAuthStore } from './hooks/useAuth';
import { getMe, getCsrfToken } from './api/client';
import { useEffect } from 'react';

// Pages
import { Dashboard } from './pages/Dashboard';
import { Models } from './pages/Models';
import { Benchmarks } from './pages/Benchmarks';
import { Hardware } from './pages/Hardware';
import { Settings } from './pages/Settings';
import { LoginCallback } from './pages/LoginCallback';

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, setUser, setLoading } = useAuthStore();

  useEffect(() => {
    async function initAuth() {
      try {
        await getCsrfToken();
        const user = await getMe();
        setUser(user);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    initAuth();
  }, [setUser, setLoading]);

  if (isLoading) {
    return <LoadingFullScreen />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Layout>{children}</Layout>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return <LoadingFullScreen />;
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><LoginCallback /></PublicRoute>} />
      <Route path="/callback" element={<LoginCallback />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/models" element={<Models />} />
              <Route path="/benchmarks" element={<Benchmarks />} />
              <Route path="/hardware" element={<Hardware />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </PrivateRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;