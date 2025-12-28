import React, { useEffect, useState } from 'react';
import api from '../api';

const Dashboard: React.FC = () => {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState({ documents: 0, sessions: 0 });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const docsResponse = await api.get('/documents/list');
        setDocuments(docsResponse.data);
        setStats({ documents: docsResponse.data.length, sessions: 0 });
      } catch (error) {
        console.error(error);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h2 className="text-4xl font-bold text-gray-900 mb-2">Dashboard</h2>
          <p className="text-gray-600 mb-8">Welcome back. Let's work with your documents.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl shadow-lg overflow-hidden transform hover:scale-105 transition duration-300">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-10 w-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-blue-100 truncate">Total Documents</dt>
                      <dd className="text-3xl font-bold text-white">{stats.documents}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-xl shadow-lg overflow-hidden transform hover:scale-105 transition duration-300">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-10 w-10 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z"/>
                      <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z"/>
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-green-100 truncate">Chat Sessions</dt>
                      <dd className="text-3xl font-bold text-white">{stats.sessions}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-white shadow-xl rounded-xl overflow-hidden border border-gray-200">
            <div className="px-6 py-5 bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
              <h3 className="text-xl leading-6 font-semibold text-gray-900 flex items-center">
                <svg className="w-6 h-6 mr-3 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z"/>
                </svg>
                Recent Documents
              </h3>
            </div>
            {documents.length === 0 ? (
              <div className="p-8 text-center">
                <h4 className="text-lg font-semibold text-gray-800">No documents yet</h4>
                <p className="text-gray-600 mt-2">Upload your first document to enable document-grounded conversations.</p>
                <div className="mt-6 flex justify-center">
                  <a href="/upload" className="inline-block bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-lg font-semibold shadow-md">Upload Document</a>
                </div>
              </div>
            ) : (
              <ul className="divide-y divide-gray-200">
                {documents.map((doc: any) => (
                  <li key={doc.id} className="hover:bg-gray-50 transition duration-200">
                    <div className="px-6 py-4">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-indigo-600 truncate flex-1">{doc.filename}</p>
                        <div className="flex space-x-3 ml-4">
                          <button
                            onClick={async () => {
                              if (confirm('Delete this document?')) {
                                try {
                                  await api.delete(`/documents/delete/${doc.id}`);
                                  setDocuments(documents.filter((d: any) => d.id !== doc.id));
                                } catch (error: any) {
                                  alert(error.response?.data?.detail || 'Delete failed');
                                }
                              }
                            }}
                            className="bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:from-red-600 hover:to-red-700 transition duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5 flex items-center"
                          >
                            <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd"/>
                            </svg>
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;