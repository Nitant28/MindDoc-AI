import React, { useEffect, useState } from 'react';
import { Plus, MessageSquare, Trash2 } from 'lucide-react';
import api from '../../api';

interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}

interface ChatSidebarProps {
  onSelectSession?: (sessionId: number) => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({ onSelectSession }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const response = await api.get('/chat/sessions');
      setSessions(response.data);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setSelectedId(null);
    if (onSelectSession) {
      onSelectSession(0);
    }
  };

  const handleSelectSession = (id: number) => {
    setSelectedId(id);
    if (onSelectSession) {
      onSelectSession(id);
    }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await api.delete(`/chat/sessions/${id}`);
      setSessions(sessions.filter((s) => s.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  return (
    <div className="w-64 bg-bg2 border-r border-bg3 flex flex-col p-4">
      <button
        onClick={handleNewChat}
        className="w-full flex items-center gap-2 px-4 py-2 rounded-lg bg-primary hover:bg-accent text-white font-semibold transition-all mb-4"
      >
        <Plus size={18} />
        New Chat
      </button>

      <div className="flex-1 overflow-y-auto space-y-2">
        {loading ? (
          <div className="text-center text-gray-400 text-sm py-4">Loading...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center text-gray-400 text-sm py-4">No chats yet</div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => handleSelectSession(session.id)}
              className={`flex items-center justify-between gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all ${
                selectedId === session.id ? 'bg-primary text-white' : 'bg-bg3 hover:bg-bg4 text-gray-300'
              }`}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <MessageSquare size={16} />
                <span className="text-sm truncate">{session.title}</span>
              </div>
              <button
                onClick={(e) => handleDeleteSession(e, session.id)}
                className="p-1 hover:bg-red-500 hover:bg-opacity-20 rounded transition-all"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ChatSidebar;
