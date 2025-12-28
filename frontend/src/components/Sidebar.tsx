import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, toggleSidebar }) => {
  const [activeSection, setActiveSection] = useState('documents');
  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [savedItems, setSavedItems] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [docsRes, sessRes, savedRes] = await Promise.all([
          api.get('/documents/list'),
          api.get('/chat/sessions'),
          api.get('/chat/saved_items')
        ]);
        setDocuments(docsRes.data);
        setSessions(sessRes.data);
        setSavedItems(savedRes.data);
      } catch (error) {
        console.error(error);
      }
    };
    fetchData();
  }, []);

  const sections = [
    { id: 'documents', label: 'Documents', icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg> },
    { id: 'sessions', label: 'Chat Sessions', icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"/><path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"/></svg> },
    { id: 'saved', label: 'Saved Items', icon: <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg> }
  ];

  return (
    <div className={`fixed inset-y-0 left-0 z-50 w-80 bg-white shadow-lg transform ${isOpen ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 ease-in-out`}>
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-xl font-bold text-gray-800">MindDoc AI</h2>
        <button onClick={toggleSidebar} className="text-gray-500 hover:text-gray-700">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div className="flex flex-col h-full">
        <div className="flex border-b">
          {sections.map(section => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`flex-1 py-3 px-2 text-center text-sm font-medium ${
                activeSection === section.id ? 'bg-blue-100 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span className="mr-1">{section.icon}</span>
              {section.label}
            </button>
          ))}
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          {activeSection === 'documents' && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Recent Documents</h3>
              <ul className="space-y-2">
                {documents.map((doc: any) => (
                  <li key={doc.id} className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100">
                    <span className="text-sm truncate flex-1">{doc.filename}</span>
                    <div className="flex space-x-1">
                      <button
                        onClick={() => window.location.href = `/chat?document=${doc.id}`}
                        className="text-blue-500 hover:text-blue-700 text-xs"
                        title="Chat"
                      >
                        💬
                      </button>
                      <button
                        onClick={async () => {
                          const isSaved = savedItems.some((item: any) => item.title === doc.filename);
                          if (isSaved) {
                            // Unsave
                            const savedItem = savedItems.find((item: any) => item.title === doc.filename);
                            if (savedItem) {
                              try {
                                await api.delete(`/chat/saved_items/${savedItem.id}`);
                                const savedRes = await api.get('/chat/saved_items');
                                setSavedItems(savedRes.data);
                              } catch (error) {
                                alert('Unsave failed');
                              }
                            }
                          } else {
                            // Save
                            try {
                              await api.post(`/documents/save/${doc.id}`);
                              const savedRes = await api.get('/chat/saved_items');
                              setSavedItems(savedRes.data);
                            } catch (error) {
                              alert('Save failed');
                            }
                          }
                        }}
                        className={`text-xs ${savedItems.some((item: any) => item.title === doc.filename) ? 'text-yellow-600' : 'text-yellow-500 hover:text-yellow-700'}`}
                        title={savedItems.some((item: any) => item.title === doc.filename) ? 'Unsave' : 'Save'}
                      >
                        {savedItems.some((item: any) => item.title === doc.filename) ? '★' : '☆'}
                      </button>
                      <button
                        onClick={async () => {
                          if (confirm('Edit filename?')) {
                            const newName = prompt('New filename:', doc.filename);
                            if (newName) {
                              try {
                                await api.put(`/documents/edit/${doc.id}`, { filename: newName });
                                const docsRes = await api.get('/documents/list');
                                setDocuments(docsRes.data);
                              } catch (error) {
                                alert('Edit failed');
                              }
                            }
                          }
                        }}
                        className="text-green-500 hover:text-green-700 text-xs"
                        title="Edit"
                      >
                        Edit
                      </button>
                      <button
                        onClick={async () => {
                          if (confirm('Delete document?')) {
                            try {
                              await api.delete(`/documents/delete/${doc.id}`);
                              const docsRes = await api.get('/documents/list');
                              setDocuments(docsRes.data);
                            } catch (error) {
                              alert('Delete failed');
                            }
                          }
                        }}
                        className="text-red-500 hover:text-red-700 text-xs"
                        title="Delete"
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
              <Link to="/upload" className="mt-4 inline-block bg-green-500 text-white px-3 py-2 rounded text-sm hover:bg-green-600">
                + Upload New
              </Link>
            </div>
          )}
          
          {activeSection === 'sessions' && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Chat Sessions</h3>
              <ul className="space-y-2">
                {sessions.map((session: any) => (
                  <li key={session.id} className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100">
                    <span className="text-sm truncate flex-1" onClick={() => window.location.href = `/chat?session=${session.id}`} style={{cursor: 'pointer'}}>{session.title}</span>
                    <div className="flex space-x-1">
                      <button
                        onClick={async () => {
                          if (confirm('Edit session title?')) {
                            const newTitle = prompt('New title:', session.title);
                            if (newTitle) {
                              try {
                                await api.put(`/chat/sessions/${session.id}`, { title: newTitle });
                                const sessRes = await api.get('/chat/sessions');
                                setSessions(sessRes.data);
                              } catch (error) {
                                alert('Edit failed');
                              }
                            }
                          }
                        }}
                        className="text-green-500 hover:text-green-700 text-xs"
                        title="Edit"
                      >
                        Edit
                      </button>
                      <button
                        onClick={async () => {
                          if (confirm('Delete session?')) {
                            try {
                              await api.delete(`/chat/sessions/${session.id}`);
                              const sessRes = await api.get('/chat/sessions');
                              setSessions(sessRes.data);
                            } catch (error) {
                              alert('Delete failed');
                            }
                          }
                        }}
                        className="text-red-500 hover:text-red-700 text-xs"
                        title="Delete"
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
              <Link to="/chat" className="mt-4 inline-block bg-blue-500 text-white px-3 py-2 rounded text-sm hover:bg-blue-600">
                + New Chat
              </Link>
            </div>
          )}
          
          {activeSection === 'saved' && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Saved Items</h3>
              <ul className="space-y-2">
                {savedItems.map((item: any) => (
                  <li key={item.id} className="p-2 bg-gray-50 rounded hover:bg-gray-100">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-500">{item.type}</span>
                      <div className="flex space-x-1">
                        <button
                          onClick={async () => {
                            if (confirm('Edit item?')) {
                              const newTitle = prompt('New title:', item.title);
                              const newContent = prompt('New content:', item.content);
                              if (newTitle && newContent) {
                                try {
                                  await api.put(`/chat/saved_items/${item.id}`, { title: newTitle, content: newContent });
                                  const savedRes = await api.get('/chat/saved_items');
                                  setSavedItems(savedRes.data);
                                } catch (error) {
                                  alert('Edit failed');
                                }
                              }
                            }
                          }}
                          className="text-green-500 hover:text-green-700 text-xs"
                          title="Edit"
                        >
                          Edit
                        </button>
                        <button
                          onClick={async () => {
                            if (confirm('Delete item?')) {
                              try {
                                await api.delete(`/chat/saved_items/${item.id}`);
                                const savedRes = await api.get('/chat/saved_items');
                                setSavedItems(savedRes.data);
                              } catch (error) {
                                alert('Delete failed');
                              }
                            }
                          }}
                          className="text-red-500 hover:text-red-700 text-xs"
                          title="Delete"
                        >
                          Delete
                        </button>
                        {item.type === 'document' && (
                          <button
                            onClick={async () => {
                              // Unsave: delete from saved items
                              try {
                                await api.delete(`/chat/saved_items/${item.id}`);
                                const savedRes = await api.get('/chat/saved_items');
                                setSavedItems(savedRes.data);
                              } catch (error) {
                                alert('Unsave failed');
                              }
                            }}
                            className="text-gray-500 hover:text-gray-700 text-xs"
                            title="Unsave"
                          >
                            Unsave
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-xs text-gray-600 truncate">{item.content}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;