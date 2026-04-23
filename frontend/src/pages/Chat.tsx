import { FC, useState } from 'react';
import Topbar from '../components/layout/Topbar';
import PageWrapper from '../components/layout/PageWrapper';
import ChatSidebar from '../components/shared/ChatSidebar';
import ChatWindow from '../components/shared/ChatWindow';

const Chat: FC = () => {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);

  return (
    <div className="flex min-h-screen bg-bg1 flex-col">
      <Topbar />
      <PageWrapper>
        <div className="flex h-[80vh] mt-8 rounded-card overflow-hidden shadow-glow glass border border-white/10">
          <ChatSidebar onSelectSession={setSelectedSessionId} />
          <ChatWindow sessionId={selectedSessionId || undefined} />
        </div>
      </PageWrapper>
    </div>
  );
};

export default Chat;