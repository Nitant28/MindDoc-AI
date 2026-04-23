import React, { useEffect, useState, useRef } from 'react';
import { Send, Loader, Paperclip, Upload as UploadIcon } from 'lucide-react';
import api from '../../api';
import FileAttachmentPanel from './FileAttachmentPanel';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface ChatWindowProps {
  sessionId?: number;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ sessionId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [showAttachments, setShowAttachments] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId && sessionId > 0) {
      fetchMessages(sessionId);
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchMessages = async (id: number) => {
    try {
      const response = await api.get(`/chat/messages/${id}`);
      setMessages(response.data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input;
    setInput('');

    // Add user message immediately (visible while waiting for LLM)
    const userMsgId = Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        role: 'user',
        content: userMessage,
        created_at: new Date().toISOString(),
      },
    ]);

    setLoading(true);

    try {
      const response = await api.post('/chat/query', {
        query: userMessage,
        session_id: sessionId && sessionId > 0 ? sessionId : undefined,
        document_id: selectedDocId || undefined,
      });

      // Add assistant response
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: 'assistant',
          content: response.data.reply,
          created_at: new Date().toISOString(),
        },
      ]);

      if (response.data.session_id) {
        // Session ID would be updated in parent component
      }
    } catch (error: any) {
      console.error('Failed to send message:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to send message';
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 2,
          role: 'assistant',
          content: `Error: ${errorMsg}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      // Add system message about upload
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: 'assistant',
          content: `Document "${file.name}" uploaded successfully! You can now ask questions about it.`,
          created_at: new Date().toISOString(),
        },
      ]);
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error: any) {
      console.error('Failed to upload file:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to upload file';
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: `Upload failed: ${errorMsg}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-bg1">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-full text-center text-gray-400">
            <div>
              <p className="text-lg font-semibold mb-2">Start a new conversation</p>
              <p className="text-sm">Upload documents or reference saved files, then ask your questions</p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-primary text-white rounded-br-none'
                    : 'bg-bg3 text-gray-200 rounded-bl-none'
                }`}
              >
                <p className="text-sm break-words">{msg.content}</p>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-bg3 text-gray-200 px-4 py-3 rounded-lg rounded-bl-none flex items-center gap-2">
              <Loader size={16} className="animate-spin" />
              <span className="text-sm">AI is analyzing...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* File Attachment Panel */}
      {showAttachments && (
        <FileAttachmentPanel
          selectedDocId={selectedDocId || undefined}
          onSelectDocument={setSelectedDocId}
          isOpen={showAttachments}
          onClose={() => setShowAttachments(false)}
        />
      )}

      {/* Input Area */}
      <div className="border-t border-bg3 bg-bg2">
        <form onSubmit={handleSend} className="flex flex-col gap-3 p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={loading || uploading}
              className="flex-1 px-4 py-2 rounded-lg bg-bg1 text-white border border-bg3 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary transition-all disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                uploading
                  ? 'bg-gray-600 text-gray-300 cursor-not-allowed'
                  : 'bg-bg3 hover:bg-bg4 text-gray-300'
              }`}
              title="Upload a document directly"
            >
              <UploadIcon size={18} />
            </button>
            <button
              type="button"
              onClick={() => setShowAttachments(!showAttachments)}
              className={`px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
                showAttachments
                  ? 'bg-primary text-white'
                  : 'bg-bg3 hover:bg-bg4 text-gray-300'
              }`}
              title="Select saved documents"
            >
              <Paperclip size={18} />
            </button>
            <button
              type="submit"
              disabled={loading || uploading || !input.trim()}
              className="px-4 py-2 rounded-lg bg-primary hover:bg-accent text-white font-semibold transition-all disabled:opacity-50 flex items-center gap-2"
            >
              <Send size={18} />
            </button>
          </div>
          {selectedDocId && (
            <div className="text-xs text-gray-400 px-2">
              📎 Document referenced - AI will use it for context
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            accept=".pdf,.txt,.doc,.docx,.xlsx,.csv"
            className="hidden"
          />
        </form>
      </div>
    </div>
  );
};

export default ChatWindow;
