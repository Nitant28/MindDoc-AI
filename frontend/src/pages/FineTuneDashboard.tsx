import React, { useState } from 'react';
import api from '../api';
import { motion } from 'framer-motion';

const FineTuneDashboard: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState('');

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError('');
    setAnalysis(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await api.post('/finetune/upload', formData);
      setAnalysis(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload or analysis failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-bg1 via-bg3 to-bg4 relative overflow-hidden">
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8 }} className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full bg-primary/40 blur-3xl z-0" />
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, delay: 0.2 }} className="absolute -bottom-32 -right-32 w-[500px] h-[500px] rounded-full bg-accent/40 blur-3xl z-0" />
      <div className="relative z-10 w-full max-w-2xl glass border border-white/10 shadow-glow rounded-card p-12 flex flex-col items-center">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="text-3xl font-syne font-extrabold gradient-text mb-4 text-center drop-shadow-2xl">Document Fine-tune & Analysis Dashboard</motion.h1>
        <form onSubmit={handleUpload} className="space-y-6 mb-6 w-full">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={e => setFile(e.target.files?.[0] || null)}
            className="w-full px-4 py-3 rounded-input bg-bg2 border border-white/10 focus:ring-2 focus:ring-primary focus:border-transparent transition duration-200 text-white placeholder-white/40"
            required
          />
          <button
            type="submit"
            disabled={uploading}
            className="w-full rounded-pill bg-gradient-to-r from-primary via-accent to-green text-white font-bold py-3 shadow-glow text-lg transition-all hover:-translate-y-1 hover:scale-110 hover:shadow-2xl focus:outline-none disabled:opacity-60 flex items-center justify-center"
          >
            {uploading ? 'Processing...' : 'Upload & Analyze'}
          </button>
        </form>
        <p className="text-gray-400 mb-4 text-center">Fine-tune and analyze any document: contracts, reports, legal files, business docs, and more. Unlock advanced AI-powered insights and custom workflows for your unique needs.</p>
        {error && <p className="text-red-500 mb-4">{error}</p>}
        {analysis && (
          <div className="w-full">
            <h2 className="text-xl font-bold mb-2 gradient-text">Analysis Results</h2>
            <ul className="space-y-4">
              {Array.isArray(analysis) ? analysis.map((clause: any, idx: number) => (
                <motion.li key={idx} whileHover={{ scale: 1.04, boxShadow: '0 8px 32px 0 rgba(0,0,0,0.25)' }} className="p-6 rounded-xl glass border border-white/10 shadow-glow transition-transform duration-300" style={{ background: clause.color }}>
                  <div className="font-semibold text-white/90 mb-1">{clause.summary}</div>
                  <div className="text-sm text-white/80 mb-1">Risk: <span className="font-bold text-accent">{clause.risk}</span></div>
                  {clause.perks && <div className="text-xs text-green">Perks: {clause.perks}</div>}
                  {clause.deadlines && <div className="text-xs text-yellow-300">Deadlines: {clause.deadlines}</div>}
                  {clause.obligations && <div className="text-xs text-blue-300">Obligations: {clause.obligations}</div>}
                  <div className="text-xs mt-2 text-white/70">{clause.clause}</div>
                </motion.li>
              )) : <pre className="bg-bg2/80 p-4 rounded-lg overflow-x-auto text-white/80 border border-white/10">{JSON.stringify(analysis, null, 2)}</pre>}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default FineTuneDashboard;
