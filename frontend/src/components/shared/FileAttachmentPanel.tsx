import React, { useEffect, useState } from 'react';
import { FileText, X, Check } from 'lucide-react';
import api from '../../api';

interface Document {
  id: number;
  filename: string;
}

interface FileAttachmentPanelProps {
  selectedDocId?: number;
  onSelectDocument?: (docId: number | null) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

const FileAttachmentPanel: React.FC<FileAttachmentPanelProps> = ({
  selectedDocId,
  onSelectDocument,
  isOpen = true,
  onClose
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      fetchDocuments();
    }
  }, [isOpen]);

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

  const handleSelectDocument = (docId: number) => {
    if (onSelectDocument) {
      onSelectDocument(selectedDocId === docId ? null : docId);
    }
  };

  const selectedDocument = documents.find((d) => d.id === selectedDocId);

  if (!isOpen) return null;

  return (
    <div className="bg-bg2 border-t border-bg3 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <FileText size={18} />
          {selectedDocument ? 'Document Attached' : 'Reference Documents'}
        </h3>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-bg3 rounded transition-all"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {selectedDocument ? (
        <div className="bg-primary/20 border border-primary rounded-lg p-4 mb-4">
          <div className="flex items-center gap-3">
            <FileText size={20} className="text-primary" />
            <div>
              <p className="text-sm font-semibold text-white">{selectedDocument.filename}</p>
              <p className="text-xs text-gray-400">Selected for AI reference</p>
            </div>
            <button
              onClick={() => handleSelectDocument(selectedDocId!)}
              className="ml-auto px-3 py-1 rounded text-sm bg-primary/30 hover:bg-primary/50 text-primary transition-all"
            >
              Remove
            </button>
          </div>
        </div>
      ) : null}

      {!selectedDocument && (
        <>
          {loading ? (
            <div className="text-center py-4 text-gray-400">Loading documents...</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-4 text-gray-400 text-sm">
              No documents uploaded yet.{' '}
              <a href="/upload" className="text-primary hover:text-accent underline">
                Upload one
              </a>
            </div>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => handleSelectDocument(doc.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg flex items-center justify-between transition-all ${
                    selectedDocId === doc.id
                      ? 'bg-primary text-white'
                      : 'bg-bg3 hover:bg-bg4 text-gray-300'
                  }`}
                >
                  <span className="flex items-center gap-2 truncate flex-1">
                    <FileText size={14} />
                    <span className="truncate text-sm">{doc.filename}</span>
                  </span>
                  {selectedDocId === doc.id && <Check size={16} />}
                </button>
              ))}
            </div>
          )}
        </>
      )}

      {selectedDocument && documents.length > 1 && (
        <div className="mt-4 pt-4 border-t border-bg3">
          <p className="text-xs text-gray-400 mb-3">Or select a different document:</p>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {documents
              .filter((d) => d.id !== selectedDocId)
              .map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => handleSelectDocument(doc.id)}
                  className="w-full text-left px-3 py-2 rounded-lg bg-bg3 hover:bg-bg4 text-gray-300 flex items-center gap-2 transition-all text-sm"
                >
                  <FileText size={14} />
                  <span className="truncate">{doc.filename}</span>
                </button>
              ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileAttachmentPanel;
