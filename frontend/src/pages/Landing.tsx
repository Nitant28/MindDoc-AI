import React, { Suspense, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';
import { FileText, AlertTriangle, Zap, CheckCircle, Lock } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);
  const [stats, setStats] = useState({
    documentsCount: '0',
    risksCount: '0',
    responseTime: '<100ms',
    uptime: '99.9%'
  });

  // Redirect to dashboard if already logged in
  React.useEffect(() => {
    if (token) {
      navigate('/dashboard');
    }
  }, [token, navigate]);

  // Format large numbers for display
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`.replace(/\.0M$/, 'M');
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`.replace(/\.0K$/, 'K');
    } else {
      return num.toString();
    }
  };

  // Fetch actual stats from backend
  useEffect(() => {
    const fetchStats = async () => {
      try {
                const response = await fetch('/api/documents/statistics');
        const data = await response.json();
        setStats({
          documentsCount: formatNumber(data.total_documents || 0),
          risksCount: formatNumber(data.risks_detected || 0),
          responseTime: data.response_time || '<100ms',
          uptime: data.uptime || '99.9%'
        });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
        // Keep default stats if API fails
        setStats({
          documentsCount: '0',
          risksCount: '0',
          responseTime: '<100ms',
          uptime: '99.9%'
        });
      }
    };

    fetchStats();
    // Refresh stats every 30 seconds for real-time updates
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-bg1 via-bg3 to-bg4">
      {/* Hero Section */}
      <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-4">
        {/* 3D Background */}
        <div className="absolute inset-0 z-0">
          <Canvas camera={{ position: [0, 0, 5], fov: 60 }}>
            <ambientLight intensity={0.7} />
            <directionalLight position={[5, 5, 5]} intensity={1.2} />
            <Suspense fallback={null}>
              <Stars radius={40} depth={80} count={3000} factor={5} fade speed={2.5} />
            </Suspense>
            <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={1.2} />
          </Canvas>
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col items-center justify-center text-center">
          <motion.h1
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-5xl md:text-7xl font-extrabold gradient-text drop-shadow-2xl mb-6 font-syne"
          >
            MindDoc AI
          </motion.h1>
          
          <motion.p
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-lg md:text-2xl text-white/80 mb-8 max-w-3xl leading-relaxed"
          >
            Read every contract. Catch every risk. In seconds.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="text-base md:text-lg text-white/60 mb-12 max-w-2xl"
          >
            Upload a PDF. MindDoc AI reads it instantly, finds the risky clauses, explains the weird terms. No more surprises at 11 PM when reviewing deals or midnight marathon review sessions.
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="flex gap-4"
          >
            <a
              href="/register"
              className="px-8 py-4 rounded-full bg-gradient-to-r from-primary via-accent to-green text-white font-bold text-lg shadow-glow hover:scale-105 transition-all"
            >
              Get Started
            </a>
            <a
              href="/login"
              className="px-8 py-4 rounded-full bg-white/10 border border-white/30 text-white font-bold text-lg hover:bg-white/20 transition-all"
            >
              Sign In
            </a>
          </motion.div>
        </div>
      </div>

      {/* Features Section */}
      <div className="relative z-10 py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl font-extrabold gradient-text mb-4">What Makes Us Different</h2>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto">
              Analyze any document in seconds. Get instant insights, spot risks before they bite you, extract what matters. Works with contracts, reports, PDFs, and everything else.
            </p>
          </motion.div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
            {[
              { icon: FileText, label: 'Contracts Analyzed', value: stats.documentsCount },
              { icon: AlertTriangle, label: 'Risks Caught', value: stats.risksCount },
              { icon: Zap, label: 'Response Time', value: stats.responseTime },
              { icon: CheckCircle, label: 'Reliability', value: stats.uptime }
            ].map((stat, i) => {
              const IconComponent = stat.icon;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: i * 0.1 }}
                  className="bg-glass rounded-xl p-6 text-center shadow-glow border border-bg3 hover:border-primary transition-all group"
                >
                  <div className="flex justify-center mb-4 text-primary group-hover:text-accent transition-colors">
                    <IconComponent size={32} strokeWidth={1.5} />
                  </div>
                  <div className="text-3xl font-bold mb-2 gradient-text">{stat.value}</div>
                  <div className="text-sm text-gray-300">{stat.label}</div>
                </motion.div>
              );
            })}
          </div>

          {/* Capabilities */}
          <div>
            <h3 className="text-2xl font-bold gradient-text mb-8 text-center">Features That Actually Matter</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  icon: FileText,
                  title: 'Read Contracts in Seconds',
                  desc: 'Upload any contract. Get key terms, obligations, and deadlines extracted automatically. No manual scrolling through hundreds of pages.'
                },
                {
                  icon: AlertTriangle,
                  title: 'Spot Risks Before They Bite',
                  desc: 'AI finds risky language, missing clauses, and liability traps. Color-coded risk scores show what matters and what doesn\'t.'
                },
                {
                  icon: Zap,
                  title: 'Ask Your Documents',
                  desc: '"What\'s the termination clause?" "When do payments start?" Get instant answers with specific quotes backing them up.'
                },
                {
                  icon: FileText,
                  title: 'One-Page Summaries',
                  desc: 'Complex contracts, investment documents, legal reports—get the essence in minutes. Perfect for busy executives who don\'t have hours to read.'
                },
                {
                  icon: CheckCircle,
                  title: 'Organize Everything Intelligently',
                  desc: 'Every clause categorized automatically. Deadlines flagged. Obligations highlighted. Compliance issues flagged. Stay on top of everything.'
                },
                {
                  icon: Lock,
                  title: 'Your Data, Your Rules',
                  desc: 'Works completely offline. No cloud uploads. No third parties. Your sensitive contracts never leave your control. Pure privacy.'
                }
              ].map((cap, i) => {
                const IconComponent = cap.icon;
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: i * 0.1 }}
                    className="bg-glass rounded-xl p-8 shadow-glow border border-bg3 hover:border-primary hover:shadow-xl transition-all group"
                  >
                    <div className="text-primary group-hover:text-accent transition-colors mb-4">
                      <IconComponent size={36} strokeWidth={1.5} />
                    </div>
                    <h4 className="font-semibold text-lg text-white mb-2">{cap.title}</h4>
                    <p className="text-gray-300 text-sm leading-relaxed">{cap.desc}</p>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative z-10 py-20 px-4 bg-gradient-to-r from-primary/10 via-accent/10 to-green/10">
        <div className="max-w-2xl mx-auto text-center">
          <h3 className="text-3xl font-bold gradient-text mb-6">Stop Drowning in Contract Reviews</h3>
          <p className="text-gray-300 mb-8">
            Read contracts instantly. Spot the risks. Move forward with confidence. Your legal team will thank you.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="/register"
              className="inline-block px-10 py-4 rounded-full bg-gradient-to-r from-primary via-accent to-green text-white font-bold text-lg shadow-glow hover:scale-105 transition-all"
            >
              Try for Free
            </a>
            <a
              href="/login"
              className="inline-block px-10 py-4 rounded-full bg-white/10 border border-white/30 text-white font-bold text-lg hover:bg-white/20 transition-all"
            >
              Already have an account?
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
