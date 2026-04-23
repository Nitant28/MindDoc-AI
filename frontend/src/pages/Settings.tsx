import React, { useState } from 'react';
import { useAuthStore } from '../stores/useAuthStore';
import { LogOut, Lock, Bell } from 'lucide-react';

const Settings: React.FC = () => {
  const { logout } = useAuthStore();
  const [notifications, setNotifications] = useState(true);
  const [theme, setTheme] = useState('dark');

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-4xl font-extrabold gradient-text mb-4">Settings & Preferences</h1>
      <p className="text-lg text-gray-300 mb-8 max-w-2xl">
        Customize your MindDoc AI experience. Control privacy, AI model options, notifications, and more.
      </p>

      <div className="space-y-6">
        {/* Notifications */}
        <div className="bg-glass rounded-xl p-6 shadow-glow border border-bg3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bell size={20} className="text-primary" />
              <div>
                <h3 className="font-semibold text-white">Notifications</h3>
                <p className="text-sm text-gray-400">Enable push notifications for document updates</p>
              </div>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${
                notifications
                  ? 'bg-primary text-white'
                  : 'bg-bg3 text-gray-300'
              }`}
            >
              {notifications ? 'On' : 'Off'}
            </button>
          </div>
        </div>

        {/* Theme */}
        <div className="bg-glass rounded-xl p-6 shadow-glow border border-bg3">
          <div className="flex items-center gap-3 mb-4">
            <Lock size={20} className="text-primary" />
            <h3 className="font-semibold text-white">Theme</h3>
          </div>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            className="w-full px-4 py-2 rounded-lg bg-bg2 text-white border border-bg3 focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="dark">Dark Mode</option>
            <option value="light">Light Mode</option>
            <option value="auto">Auto (System)</option>
          </select>
        </div>

        {/* Privacy & Security */}
        <div className="bg-glass rounded-xl p-6 shadow-glow border border-bg3">
          <div className="flex items-center gap-3 mb-4">
            <Lock size={20} className="text-primary" />
            <h3 className="font-semibold text-white">Privacy & Security</h3>
          </div>
          <p className="text-gray-400 mb-4 text-sm">
            Your documents are encrypted and stored locally. All data is private and secure.
          </p>
          <button className="px-4 py-2 rounded-lg bg-bg3 hover:bg-bg4 text-white font-medium transition-all">
            View Privacy Policy
          </button>
        </div>

        {/* Logout */}
        <div className="bg-glass rounded-xl p-6 shadow-glow border border-red-500/30">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-white">Sign Out</h3>
              <p className="text-sm text-gray-400">End your current session</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 font-medium transition-all"
            >
              <LogOut size={18} />
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;