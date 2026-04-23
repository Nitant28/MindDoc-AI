import React from 'react';
import { useAuthStore } from '../../stores/useAuthStore';
import { LogOut, User } from 'lucide-react';

const Topbar: React.FC = () => {
  const { logout } = useAuthStore();
  const token = useAuthStore((s) => s.token);

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  return (
    <div className="h-16 bg-bg2 border-b border-bg3 flex items-center justify-between px-6 shadow-sm">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-bold gradient-text">Chat</h1>
      </div>
      <div className="flex items-center gap-4">
        {token && (
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-bg3 hover:bg-bg4 text-white transition-all"
          >
            <LogOut size={18} />
            <span className="text-sm">Logout</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default Topbar;
