import React from 'react';
import { AlertTriangle, Clock, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface Clause {
  type: 'risk' | 'deadline' | 'safe';
  title: string;
  description: string;
  severity?: 'high' | 'medium' | 'low';
}

interface DocumentAnalysisPanelProps {
  filename: string;
  isOpen: boolean;
  onClose: () => void;
}

const DocumentAnalysisPanel: React.FC<DocumentAnalysisPanelProps> = ({
  filename,
  isOpen,
  onClose
}) => {
  // Mock analysis data - in production, this would come from backend
  const mockClauses: Clause[] = [
    {
      type: 'risk',
      title: 'Liability Clause',
      description: 'Unlimited liability for breach of contract detected',
      severity: 'high'
    },
    {
      type: 'deadline',
      title: 'Payment Due Date',
      description: 'Payment due within 30 days from invoice date',
      severity: 'medium'
    },
    {
      type: 'risk',
      title: 'Termination Rights',
      description: 'Non-compete clause extends 3 years after termination',
      severity: 'medium'
    },
    {
      type: 'deadline',
      title: 'Renewal Date',
      description: 'Contract auto-renews unless notice given 60 days prior',
      severity: 'high'
    },
    {
      type: 'safe',
      title: 'Standard Confidentiality',
      description: 'Industry-standard confidentiality clause - low risk',
      severity: 'low'
    },
    {
      type: 'safe',
      title: 'Governing Law Clear',
      description: 'Jurisdiction clearly specified - no ambiguity',
      severity: 'low'
    }
  ];

  const riskClauses = mockClauses.filter(c => c.type === 'risk');
  const deadlineClauses = mockClauses.filter(c => c.type === 'deadline');
  const safeClauses = mockClauses.filter(c => c.type === 'safe');

  const getColorClass = (type: Clause['type']) => {
    switch (type) {
      case 'risk':
        return 'from-red-900/30 via-bg2 to-bg3 border-red-500/30 hover:border-red-400';
      case 'deadline':
        return 'from-yellow-900/30 via-bg2 to-bg3 border-yellow-500/30 hover:border-yellow-400';
      case 'safe':
        return 'from-green-900/30 via-bg2 to-bg3 border-green-500/30 hover:border-green-400';
      default:
        return '';
    }
  };

  const getIcon = (type: Clause['type']) => {
    switch (type) {
      case 'risk':
        return <AlertTriangle size={20} className="text-red-400" />;
      case 'deadline':
        return <Clock size={20} className="text-yellow-400" />;
      case 'safe':
        return <CheckCircle size={20} className="text-green-400" />;
    }
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-md flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.95 }}
        animate={{ scale: 1 }}
        className="bg-gradient-to-br from-bg1 to-bg2 rounded-xl shadow-2xl border border-bg3 max-h-[90vh] overflow-y-auto w-full max-w-3xl"
      >
        {/* Header */}
        <div className="sticky top-0 bg-bg2 border-b border-bg3 p-6 flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Document Analysis</h2>
            <p className="text-gray-400 text-sm">{filename}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-bg3 rounded-lg transition-all"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-red-400 mb-1">{riskClauses.length}</p>
              <p className="text-sm text-gray-400">Risks Detected</p>
            </div>
            <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-yellow-400 mb-1">{deadlineClauses.length}</p>
              <p className="text-sm text-gray-400">Important Dates</p>
            </div>
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-green-400 mb-1">{safeClauses.length}</p>
              <p className="text-sm text-gray-400">Safe / Clear</p>
            </div>
          </div>

          {/* Risk Clauses */}
          {riskClauses.length > 0 && (
            <div>
              <h3 className="text-lg font-bold text-red-400 mb-4 flex items-center gap-2">
                <AlertTriangle size={20} />
                Risk Alerts ({riskClauses.length})
              </h3>
              <div className="space-y-3">
                {riskClauses.map((clause, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`bg-gradient-to-r ${getColorClass(clause.type)} rounded-lg p-4 border transition-all`}
                  >
                    <div className="flex items-start gap-3">
                      {getIcon(clause.type)}
                      <div className="flex-1">
                        <p className="font-semibold text-white">{clause.title}</p>
                        <p className="text-sm text-gray-300 mt-1">{clause.description}</p>
                      </div>
                      {clause.severity && (
                        <span className={`px-3 py-1 rounded text-xs font-bold whitespace-nowrap ${
                          clause.severity === 'high' ? 'bg-red-500/30 text-red-300' :
                          clause.severity === 'medium' ? 'bg-yellow-500/30 text-yellow-300' :
                          'bg-green-500/30 text-green-300'
                        }`}>
                          {clause.severity.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Deadline Clauses */}
          {deadlineClauses.length > 0 && (
            <div>
              <h3 className="text-lg font-bold text-yellow-400 mb-4 flex items-center gap-2">
                <Clock size={20} />
                Important Deadlines ({deadlineClauses.length})
              </h3>
              <div className="space-y-3">
                {deadlineClauses.map((clause, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`bg-gradient-to-r ${getColorClass(clause.type)} rounded-lg p-4 border transition-all`}
                  >
                    <div className="flex items-start gap-3">
                      {getIcon(clause.type)}
                      <div className="flex-1">
                        <p className="font-semibold text-white">{clause.title}</p>
                        <p className="text-sm text-gray-300 mt-1">{clause.description}</p>
                      </div>
                      {clause.severity && (
                        <span className={`px-3 py-1 rounded text-xs font-bold whitespace-nowrap ${
                          clause.severity === 'high' ? 'bg-red-500/30 text-red-300' :
                          clause.severity === 'medium' ? 'bg-yellow-500/30 text-yellow-300' :
                          'bg-green-500/30 text-green-300'
                        }`}>
                          {clause.severity.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Safe Clauses */}
          {safeClauses.length > 0 && (
            <div>
              <h3 className="text-lg font-bold text-green-400 mb-4 flex items-center gap-2">
                <CheckCircle size={20} />
                Safe & Clear ({safeClauses.length})
              </h3>
              <div className="space-y-3">
                {safeClauses.map((clause, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`bg-gradient-to-r ${getColorClass(clause.type)} rounded-lg p-4 border transition-all`}
                  >
                    <div className="flex items-start gap-3">
                      {getIcon(clause.type)}
                      <div className="flex-1">
                        <p className="font-semibold text-white">{clause.title}</p>
                        <p className="text-sm text-gray-300 mt-1">{clause.description}</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default DocumentAnalysisPanel;
