import React from 'react';

interface PageWrapperProps {
  children: React.ReactNode;
}

const PageWrapper: React.FC<PageWrapperProps> = ({ children }) => {
  return (
    <div className="flex-1 flex flex-col p-6 overflow-auto">
      {children}
    </div>
  );
};

export default PageWrapper;
