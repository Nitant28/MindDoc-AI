import React, { useState } from 'react';
import api from '../api';

const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await api.post('/auth/register', { email, password });
      localStorage.setItem('token', response.data.access_token);
      window.location.href = '/dashboard';
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 border border-gray-200">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-8 animate-float">
            <svg width="96" height="96" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <defs>
                <linearGradient id="md-gradient-register" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#2b6ef6"/>
                  <stop offset="60%" stopColor="#6d28d9"/>
                </linearGradient>
                <radialGradient id="md-glow-register" cx="50%" cy="30%" r="50%">
                  <stop offset="0%" stopColor="#ffffff" stopOpacity="0.35"/>
                  <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
                </radialGradient>
                <filter id="md-drop-register" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#0b3b91" floodOpacity="0.08"/>
                </filter>
              </defs>
              <g filter="url(#md-drop-register)">
                <path d="M12 62 L12 30 Q12 26 16 26 L60 26 Q64 26 64 30 L64 62 Q64 66 60 66 L16 66 Q12 66 12 62 Z" fill="#ffffff" stroke="#e6f0ff" strokeWidth="0.8"/>
                <path d="M60 26 L64 30 L56 30 Z" fill="#eef6ff" opacity="0.9"/>
                <line x1="18" y1="36" x2="58" y2="36" stroke="#cfe7ff" strokeWidth="1" opacity="0.9"/>
                <line x1="18" y1="42" x2="52" y2="42" stroke="#e6f4ff" strokeWidth="1" opacity="0.8"/>
                <line x1="18" y1="48" x2="56" y2="48" stroke="#eaf6ff" strokeWidth="1" opacity="0.75"/>
              </g>
              <g transform="translate(20,6)">
                <g transform="scale(0.9)">
                  <path d="M20 14 C12 14 8 20 8 24 C4 24 2 28 2 32 C2 36 6 40 12 40 H44 C52 40 58 34 58 28 C58 24 54 18 48 18 C46 12 40 8 34 10 C30 6 24 6 20 14 Z" fill="url(#md-gradient-register)" />
                  <path d="M12 22 C10 18 14 14 18 14 C22 10 30 10 34 14 C40 12 46 16 48 20" fill="url(#md-glow-register)" opacity="0.6" />
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
              <ellipse cx="50" cy="82" rx="22" ry="4" fill="#0b3b91" opacity="0.06"/>
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-3">Join MindDoc AI</h1>
          <p className="text-lg text-gray-600">Create your account to get started</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-gray-700 font-semibold mb-2">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition duration-200 bg-gray-50 hover:bg-white"
              placeholder="Enter your email"
              required
            />
          </div>
          <div>
            <label className="block text-gray-700 font-semibold mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent transition duration-200 bg-gray-50 hover:bg-white"
              placeholder="Enter your password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 transition duration-300 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating Account...' : 'Register'}
          </button>
        </form>
        <p className="mt-6 text-center text-gray-600 text-sm">
          Already have an account? <a href="/login" className="text-blue-600 hover:text-blue-700 font-semibold underline">Login here</a>
        </p>
      </div>
    </div>
  );
};

export default Register;