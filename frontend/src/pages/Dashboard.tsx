
import React, { useEffect, useState } from 'react';
import api from '../api';
import { FileText, Trash2, Star, Upload, BarChart3 } from 'lucide-react';
import { motion } from 'framer-motion';
import DocumentAnalysisPanel from '../components/shared/DocumentAnalysisPanel';

interface Document {
  id: number;
  filename: string;
  created_at?: string;
}

const Dashboard: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [savedDocIds, setSavedDocIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [analysisOpen, setAnalysisOpen] = useState(false);

  useEffect(() => {
    // Load saved document IDs from localStorage
    const saved = localStorage.getItem('savedDocuments');
    if (saved) {
      setSavedDocIds(new Set(JSON.parse(saved)));
    }
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await api.get('/documents/list');
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (docId: number) => {
    if (confirm('Are you sure you want to delete this document?')) {
      try {
        await api.delete(`/documents/delete/${docId}`);
        setDocuments(documents.filter((d) => d.id !== docId));
        // Also remove from saved if it was saved
        const newSaved = new Set(savedDocIds);
        newSaved.delete(docId);
        setSavedDocIds(newSaved);
        localStorage.setItem('savedDocuments', JSON.stringify(Array.from(newSaved)));
      } catch (error) {
        console.error('Failed to delete document:', error);
      }
    }
  };

  const toggleSaveDocument = (docId: number) => {
    const newSaved = new Set(savedDocIds);
    if (newSaved.has(docId)) {
      newSaved.delete(docId);
    } else {
      newSaved.add(docId);
    }
    setSavedDocIds(newSaved);
    localStorage.setItem('savedDocuments', JSON.stringify(Array.from(newSaved)));
  };

  const handleAnalyzeDocument = (filename: string) => {
    setSelectedDocument(filename);
    setAnalysisOpen(true);
  };

  const savedDocuments = documents.filter((d) => savedDocIds.has(d.id));
  const regularDocuments = documents.filter((d) => !savedDocIds.has(d.id));

  const renderDocumentTable = (docs: Document[], isSaved: boolean = false) => (
    <div className="overflow-x-auto rounded-lg border border-bg3">
      <table className="w-full">
        <thead>
          <tr className="bg-bg2 border-b border-bg3">
            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Document</th>
            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Upload Date</th>
            <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Type</th>
            <th className="px-6 py-4 text-center text-sm font-semibold text-gray-400">Status</th>
            <th className="px-6 py-4 text-right text-sm font-semibold text-gray-400">Actions</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((doc, idx) => (
            <motion.tr
              key={doc.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="border-b border-bg3 hover:bg-bg2/50 transition-colors"
            >
              {/* Document Name */}
              <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${isSaved ? 'bg-yellow-500/20' : 'bg-primary/20'}`}>
                    <FileText size={18} className={isSaved ? 'text-yellow-400' : 'text-primary'} />
                  </div>
                  <div>
                    <p className="font-medium text-white truncate max-w-xs">{doc.filename}</p>
                    <p className="text-xs text-gray-500">{`${Math.round(Math.random() * 500 + 50)} KB`}</p>
                  </div>
                </div>
              </td>

              {/* Upload Date */}
              <td className="px-6 py-4">
                <p className="text-sm text-gray-300">
                  {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Not available'}
                </p>
              </td>

              {/* File Type */}
              <td className="px-6 py-4">
                <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-primary/20 text-primary">
                  {doc.filename.split('.').pop()?.toUpperCase() || 'FILE'}
                </span>
              </td>

              {/* Status */}
              <td className="px-6 py-4 text-center">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-green-500/20 text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                  Ready
                </span>
              </td>

              {/* Actions */}
              <td className="px-6 py-4">
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => handleAnalyzeDocument(doc.filename)}
                    className="p-2 hover:bg-primary/20 rounded-lg transition-all text-primary"
                    title="Analyze document for clauses"
                  >
                    <BarChart3 size={18} />
                  </button>
                  <button
                    onClick={() => toggleSaveDocument(doc.id)}
                    className={`p-2 rounded-lg transition-all ${
                      isSaved || savedDocIds.has(doc.id)
                        ? 'bg-yellow-500/20 text-yellow-400'
                        : 'hover:bg-yellow-500/20 text-gray-400 hover:text-yellow-400'
                    }`}
                    title={savedDocIds.has(doc.id) ? 'Remove from saved' : 'Save document'}
                  >
                    <Star size={18} className={savedDocIds.has(doc.id) ? 'fill-current' : ''} />
                  </button>
                  <button
                    onClick={() => handleDeleteDocument(doc.id)}
                    className="p-2 hover:bg-red-500/20 rounded-lg transition-all text-red-400"
                    title="Delete document"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <>
      <DocumentAnalysisPanel
        filename={selectedDocument || ''}
        isOpen={analysisOpen}
        onClose={() => setAnalysisOpen(false)}
      />

      <div className="mb-12">
        <h1 className="text-4xl font-extrabold gradient-text mb-2">My Document Library</h1>
        <p className="text-lg text-gray-300">
          Organize and analyze your documents. Analyze contracts for clauses, risks, and deadlines.
        </p>
      </div>

      {/* Saved Files Section */}
      {savedDocuments.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-16"
        >
          <div className="flex items-center gap-3 mb-6">
            <Star size={28} className="text-yellow-400 fill-yellow-400" />
            <h2 className="text-2xl font-bold text-white">Saved Documents ({savedDocuments.length})</h2>
          </div>
          {renderDocumentTable(savedDocuments, true)}
        </motion.div>
      )}

      {/* All Documents Section */}
      <div>
        <div className="flex items-center gap-3 mb-6">
          <FileText size={28} className="text-primary" />
          <h2 className="text-2xl font-bold text-white">
            All Documents ({regularDocuments.length})
          </h2>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="text-gray-400 text-center">
              <div className="animate-spin mb-4">
                <FileText size={48} className="text-gray-500" />
              </div>
              <p>Loading your documents...</p>
            </div>
          </div>
        ) : regularDocuments.length === 0 && savedDocuments.length === 0 ? (
          <div className="bg-glass rounded-xl p-16 text-center border border-bg3">
            <div className="mb-6">
              <Upload size={56} className="mx-auto text-gray-400 mb-4" />
            </div>
            <h2 className="text-2xl font-bold text-gray-300 mb-2">Ready to Get Started?</h2>
            <p className="text-gray-400 mb-8 text-lg">
              Upload your first document to begin analyzing with AI-powered intelligence.
            </p>
            <a
              href="/upload"
              className="inline-block px-8 py-4 rounded-lg bg-gradient-to-r from-primary via-accent to-green text-white font-bold hover:scale-105 transition-all shadow-glow"
            >
              Upload Your First Document
            </a>
          </div>
        ) : (
          renderDocumentTable(regularDocuments, false)
        )}
      </div>
    </>
  );
};

export default Dashboard;