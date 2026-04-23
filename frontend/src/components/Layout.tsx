import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';
import { motion } from 'framer-motion';

// Professional SVG icons for navigation
const DashboardIcon = () => (
  <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="2" fill="currentColor"/><rect x="14" y="3" width="7" height="7" rx="2" fill="currentColor"/><rect x="14" y="14" width="7" height="7" rx="2" fill="currentColor"/><rect x="3" y="14" width="7" height="7" rx="2" fill="currentColor"/></svg>
);
const UploadIcon = () => (
  <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><path d="M12 16V4M12 4l-4 4M12 4l4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/><rect x="4" y="16" width="16" height="4" rx="2" fill="currentColor"/></svg>
);
const ChatIcon = () => (
  <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
);
const ReminderIcon = () => (
  <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/><path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
);
const SettingsIcon = () => (
  <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09c0 .66.38 1.26 1 1.51a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09c0 .66.38 1.26 1 1.51H21a2 2 0 0 1 0 4h-.09c-.66 0-1.26.38-1.51 1z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
);

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
  { to: '/upload', label: 'Upload', icon: <UploadIcon /> },
  { to: '/chat', label: 'Chat', icon: <ChatIcon /> },
  { to: '/reminders', label: 'Reminders', icon: <ReminderIcon /> },
  { to: '/settings', label: 'Settings', icon: <SettingsIcon /> },
];

export function Layout() {
  const user = useAuthStore((s: any) => s.user);
  const logout = useAuthStore((s: any) => s.logout);
  const navigate = useNavigate();

  // Check authentication
  if (!user && !localStorage.getItem('token')) {
    navigate('/login');
    return null;
  }

  return (
    <div className="flex h-screen bg-bg3">
      <aside className="w-52 bg-glass border-r border-white/10 flex flex-col py-6 px-4">
        <div className="mb-8 flex items-center gap-2">
          <span className="w-3 h-3 bg-green rounded-full animate-pulse"></span>
          <span className="font-syne font-bold text-lg gradient-text">MindDoc AI</span>
        </div>
        <nav className="flex-1 flex flex-col gap-2">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2 rounded-pill font-medium transition-all ${
                  isActive ? 'bg-primary/15 text-accent' : 'hover:bg-glass hover:scale-105'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={logout}
          className="mt-8 w-full py-2 rounded-pill bg-red/80 text-white font-bold shadow-glow hover:scale-105 transition-all"
        >
          Logout
        </button>
      </aside>
      <main className="flex-1 flex flex-col">
        <header className="h-16 flex items-center px-8 border-b border-white/10 bg-glass">
          <span className="font-syne text-xl font-bold gradient-text">Welcome, {user?.name || user?.email}</span>
        </header>
        <motion.section
          className="flex-1 overflow-y-auto p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Outlet />
        </motion.section>
      </main>
    </div>
  );
}