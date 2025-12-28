import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import Sidebar from './Sidebar';
import Logo from './Logo';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black bg-opacity-50" onClick={toggleSidebar}></div>
      )}
      
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} toggleSidebar={toggleSidebar} />
      
      {/* Main Content */}
      <div className="flex flex-col min-h-screen">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <button
                  onClick={toggleSidebar}
                  className="mr-4 p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <Link to="/dashboard" className="flex items-center relative">
                  <div className="animate-float">
                    <svg width="48" height="48" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                      <defs>
                        <linearGradient id="md-gradient" x1="0" y1="0" x2="1" y2="1">
                          <stop offset="0%" stopColor="#2b6ef6"/>
                          <stop offset="60%" stopColor="#6d28d9"/>
                        </linearGradient>
                        <radialGradient id="md-glow" cx="50%" cy="30%" r="50%">
                          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.35"/>
                          <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
                        </radialGradient>
                        <filter id="md-drop" x="-20%" y="-20%" width="140%" height="140%">
                          <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#0b3b91" floodOpacity="0.08"/>
                        </filter>
                      </defs>

                      {/* Paper with folded corner */}
                      <g filter="url(#md-drop)">
                        <path d="M12 62 L12 30 Q12 26 16 26 L60 26 Q64 26 64 30 L64 62 Q64 66 60 66 L16 66 Q12 66 12 62 Z" fill="#ffffff" stroke="#e6f0ff" strokeWidth="0.8"/>
                        <path d="M60 26 L64 30 L56 30 Z" fill="#eef6ff" opacity="0.9"/>
                        <line x1="18" y1="36" x2="58" y2="36" stroke="#cfe7ff" strokeWidth="1" opacity="0.9"/>
                        <line x1="18" y1="42" x2="52" y2="42" stroke="#e6f4ff" strokeWidth="1" opacity="0.8"/>
                        <line x1="18" y1="48" x2="56" y2="48" stroke="#eaf6ff" strokeWidth="1" opacity="0.75"/>
                      </g>

                      {/* Cloud / Brain with gradient */}
                      <g transform="translate(20,6)">
                        <g transform="scale(0.9)">
                          <path d="M20 14 C12 14 8 20 8 24 C4 24 2 28 2 32 C2 36 6 40 12 40 H44 C52 40 58 34 58 28 C58 24 54 18 48 18 C46 12 40 8 34 10 C30 6 24 6 20 14 Z" fill="url(#md-gradient)" />
                          <path d="M12 22 C10 18 14 14 18 14 C22 10 30 10 34 14 C40 12 46 16 48 20" fill="url(#md-glow)" opacity="0.6" />

                          {/* network overlay */}
                          <g stroke="#ffffff" strokeWidth="0.9" strokeOpacity="0.85" fill="#ffffff">
                            <line x1="18" y1="24" x2="28" y2="20" strokeOpacity="0.35"/>
                            <line x1="28" y1="20" x2="40" y2="24" strokeOpacity="0.35"/>
                            <line x1="24" y1="28" x2="34" y2="30" strokeOpacity="0.35"/>
                            <circle cx="18" cy="24" r="1.4"/>
                            <circle cx="28" cy="20" r="1.8"/>
                            <circle cx="40" cy="24" r="1.4"/>
                            <circle cx="34" cy="30" r="1.3"/>
                          </g>
                        </g>
                      </g>

                      {/* subtle ground shadow */}
                      <ellipse cx="50" cy="82" rx="22" ry="4" fill="#0b3b91" opacity="0.06"/>
                    </svg>
                  </div>
                  <div className="ml-3">
                    <span className="text-xl font-bold text-gray-800">MindDoc AI</span>
                    <p className="text-xs text-gray-600">Intelligence, grounded in your documents</p>
                  </div>
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link to="/upload" className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700">
                  Upload
                </Link>
                <Link to="/dashboard" className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                  Dashboard
                </Link>
                <Link to="/chat" className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                  Chat
                </Link>
                <Link to="/settings" className="text-gray-700 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                  Settings
                </Link>
              </div>
            </div>
          </div>
        </header>
        
        {/* Page Content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;