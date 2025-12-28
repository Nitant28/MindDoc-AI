import React, { useState, useEffect } from 'react';
import api from '../api';

const Chat: React.FC = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState<number | null>(null);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const docId = urlParams.get('document');
    if (docId) {
      setSelectedDocument(parseInt(docId));
    }
    const fetchSessions = async () => {
      try {
        const response = await api.get('/chat/sessions');
        setSessions(response.data);
      } catch (error: any) {
        alert(error.response?.data?.detail || 'Failed to load sessions');
      }
    };
    const fetchDocuments = async () => {
      try {
        const response = await api.get('/documents/list');
        setDocuments(response.data);
      } catch (error: any) {
        console.error(error);
      }
    };
    fetchSessions();
    fetchDocuments();
  }, []);

  const fetchMessages = async (sessionId: number) => {
    try {
      const response = await api.get(`/chat/messages/${sessionId}`);
      setMessages(response.data);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to load messages');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;
    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setIsTyping(true);
    try {
      const response = await api.post('/chat/query', { query, session_id: currentSession, document_id: selectedDocument });
      const assistantMessage = { role: 'assistant', content: response.data.answer };
      setMessages(prev => [...prev, assistantMessage]);
      if (!currentSession) {
        setCurrentSession(response.data.session_id);
        // Fetch updated sessions
        const sessionsResponse = await api.get('/chat/sessions');
        setSessions(sessionsResponse.data);
      }
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Query failed');
      // Remove the user message if failed
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div className="px-4 py-6 sm:px-0">
        <div className="flex">
          <div className="w-1/4 bg-white p-4 rounded-lg shadow mr-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z"/>
              </svg>
              Chat Sessions
            </h3>
            <ul>
              {sessions.map((session: any) => (
                <li key={session.id} className="mb-2 flex items-center justify-between cursor-pointer" onClick={() => { setCurrentSession(session.id); fetchMessages(session.id); }}>
                  <span className="flex-1">{session.title}</span>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (confirm('Are you sure you want to delete this session?')) {
                        try {
                          await api.delete(`/chat/sessions/${session.id}`);
                          setSessions(sessions.filter((s: any) => s.id !== session.id));
                          if (currentSession === session.id) {
                            setCurrentSession(null);
                            setMessages([]);
                          }
                        } catch (error) {
                          alert('Failed to delete session');
                        }
                      }
                    }}
                    className="text-red-500 hover:text-red-700 ml-2"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
            <h3 className="text-lg font-semibold mb-4 mt-6 flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Recent Documents
            </h3>
            <ul>
              {documents.slice(0, 5).map((doc: any) => (
                <li key={doc.id} className={`mb-2 p-2 rounded flex items-center justify-between ${selectedDocument === doc.id ? 'bg-blue-100' : 'hover:bg-gray-100'}`}>
                  <span className="cursor-pointer flex-1 text-sm" onClick={() => setSelectedDocument(doc.id)}>{doc.filename}</span>
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      if (confirm('Delete this document?')) {
                        try {
                          await api.delete(`/documents/delete/${doc.id}`);
                          const docsResponse = await api.get('/documents/list');
                          setDocuments(docsResponse.data);
                          if (selectedDocument === doc.id) setSelectedDocument(null);
                        } catch (error) {
                          alert('Failed to delete document');
                        }
                      }
                    }}
                    className="text-red-500 hover:text-red-700 ml-2 flex-shrink-0"
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="w-3/4 bg-white p-6 rounded-lg shadow-lg border border-gray-200">
            <div className="h-96 overflow-y-auto mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              {messages.length === 0 && !isTyping ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <p className="text-gray-500 text-lg">Start a conversation with your documents.</p>
                    <p className="text-gray-400 text-sm mt-2">Upload a document or ask a question to begin.</p>
                  </div>
                </div>
              ) : (
                <>
                  {messages.map((msg: any, index) => (
                    <div key={index} className={`mb-4 flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg shadow-sm ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-white text-gray-800 border border-gray-200'}`}>
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                        {msg.role === 'assistant' && (
                          <button
                            onClick={async () => {
                              try {
                                await api.post('/chat/save_response', { title: `Saved Response ${index}`, content: msg.content });
                                alert('Response saved!');
                              } catch (error) {
                                alert('Save failed');
                              }
                            }}
                            className="mt-2 text-xs text-blue-500 hover:text-blue-700"
                          >
                            Save
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                  {isTyping && (
                    <div className="flex justify-start mb-4">
                      <div className="bg-white text-gray-800 shadow-sm px-4 py-3 rounded-lg border border-gray-200">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
            <form onSubmit={handleSubmit}>
              {selectedDocument ? (
                <div className="mb-2 text-sm text-gray-600 flex items-center justify-between">
                  <span>Using: {documents.find((d: any) => d.id === selectedDocument)?.filename || 'Selected document'}</span>
                  <button
                    type="button"
                    onClick={() => setSelectedDocument(null)}
                    className="text-red-500 hover:text-red-700 text-xs"
                  >
                    Detach
                  </button>
                </div>
              ) : null}
              <div className="flex space-x-2 mb-2">
                <input
                  type="file"
                  accept=".pdf,.docx,.png,.jpg,.jpeg,.tiff,.bmp,.txt"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                        const formData = new FormData();
                        formData.append('file', file);
                        try {
                          const response = await api.post('/documents/upload', formData);
                          alert('Document uploaded and ready for chat!');
                          setSelectedDocument(response.data.document_id);
                          // Refresh documents
                          const docsResponse = await api.get('/documents/list');
                          setDocuments(docsResponse.data);
                        } catch (error) {
                          alert(error.response?.data?.detail || 'Upload failed');
                        }
                      }
                  }}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white shadow-sm"
                />
                <button type="button" className="px-4 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
                  Attach
                </button>
              </div>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white shadow-sm"
                  placeholder="Ask a question about your documents…"
                />
                <button type="submit" className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all duration-200 flex items-center justify-center font-semibold shadow-lg">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.409l-7-14z"/>
                  </svg>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;