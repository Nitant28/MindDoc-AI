import { lazy, type ReactElement } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Layout from './components/Layout';
import { ConfirmProvider } from './components/ui/Dialog';
import { ToastProvider } from './components/ui/Toast';
import { getToken } from './lib/storage';
import { ThemeProvider } from './lib/theme';
import Chat from './pages/Chat';
import Dashboard from './pages/Dashboard';
import DocumentPage from './pages/DocumentPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Settings from './pages/Settings';
import Upload from './pages/Upload';

// Heavier, less-visited pages are code-split.
const GraphPage = lazy(() => import('./pages/Graph'));
const Vision = lazy(() => import('./pages/Vision'));
const System = lazy(() => import('./pages/System'));
const Timeline = lazy(() => import('./pages/Timeline'));
const Parties = lazy(() => import('./pages/Parties'));
const Findings = lazy(() => import('./pages/Findings'));
const Cases = lazy(() => import('./pages/Cases'));
const Discoveries = lazy(() => import('./pages/Discoveries'));

/** Protected shell: no token → /login (remembering where the user was going). */
function RequireAuth() {
  const location = useLocation();
  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return <Layout />;
}

function PublicOnly({ children }: { children: ReactElement }) {
  return getToken() ? <Navigate to="/dashboard" replace /> : children;
}

function RootRedirect() {
  return <Navigate to={getToken() ? '/dashboard' : '/login'} replace />;
}

export default function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <ConfirmProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              <Route
                path="/login"
                element={
                  <PublicOnly>
                    <Login />
                  </PublicOnly>
                }
              />
              <Route
                path="/register"
                element={
                  <PublicOnly>
                    <Register />
                  </PublicOnly>
                }
              />
              <Route element={<RequireAuth />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/documents" element={<Navigate to="/upload" replace />} />
                <Route path="/documents/:id" element={<DocumentPage />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/graph" element={<GraphPage />} />
                <Route path="/timeline" element={<Timeline />} />
                <Route path="/parties" element={<Parties />} />
                <Route path="/findings" element={<Findings />} />
                <Route path="/cases" element={<Cases />} />
                <Route path="/discoveries" element={<Discoveries />} />
                <Route path="/vision" element={<Vision />} />
                <Route path="/system" element={<System />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
              <Route path="/" element={<RootRedirect />} />
              <Route path="*" element={<RootRedirect />} />
            </Routes>
          </BrowserRouter>
        </ConfirmProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
