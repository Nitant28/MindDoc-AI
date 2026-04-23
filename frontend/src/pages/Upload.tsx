import React, { useState } from 'react';
import api from '../api';
import { motion } from 'framer-motion';

const Upload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError('');
    setProgress(0);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post('/documents/upload', formData, {
        onUploadProgress: (p) => {
          const total = p.total || 1;
          setProgress(Math.round((p.loaded / total) * 100));
        }
      });
      setProgress(100);
      alert('Document uploaded successfully');
      window.location.href = '/dashboard';
    } catch (error: any) {
      console.error('Upload error:', error.response?.data || error.message);
      const msg = error.response?.data?.detail || error.message || 'Upload failed';
      setError(msg);
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-bg1 via-bg3 to-bg4 relative overflow-hidden">
      {loading && (
        <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
          <div className="glass rounded-lg p-8 flex flex-col items-center shadow-xl border border-white/10">
            <svg className="animate-spin h-8 w-8 text-primary mb-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span className="text-lg font-semibold text-primary">Processing document...</span>
          </div>
        </div>
      )}
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8 }} className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full bg-primary/40 blur-3xl z-0" />
      <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, delay: 0.2 }} className="absolute -bottom-32 -right-32 w-[500px] h-[500px] rounded-full bg-accent/40 blur-3xl z-0" />
      <div className="relative z-10 w-full max-w-md glass border border-white/10 shadow-glow rounded-card p-10 flex flex-col items-center">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-primary to-accent rounded-full flex items-center justify-center shadow-lg">
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
              </svg>
            </div>
          </div>
          <h1 className="text-3xl font-bold gradient-text mb-2 flex items-center justify-center drop-shadow-2xl">
            <svg className="w-8 h-8 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
            </svg>
            Upload Document
          </h1>
          <p className="text-white/70">Upload a PDF, DOCX, or image file to get started</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6 w-full">
          <div className="group">
            <label className="block text-white/80 font-semibold mb-3 flex items-center">Select PDF, DOCX, or Image File</label>
            <input
              type="file"
              accept=".pdf,.docx,.png,.jpg,.jpeg,.tiff,.bmp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full px-4 py-3 rounded-input bg-bg2 border border-white/10 focus:ring-2 focus:ring-primary focus:border-transparent transition duration-200 text-white placeholder-white/40 group-hover:scale-105 group-hover:shadow-glow"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-pill bg-gradient-to-r from-primary via-accent to-green text-white font-bold py-3 shadow-glow text-lg transition-all hover:-translate-y-1 hover:scale-110 hover:shadow-2xl focus:outline-none disabled:opacity-60 flex items-center justify-center"
          >
            {loading ? 'Processing...' : 'Upload & Analyze'}
          </button>
        </form>
        {error && <p className="text-red-500 mb-4">{error}</p>}
      </div>
    </div>
  );
};

export default Upload;