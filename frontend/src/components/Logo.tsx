import React from 'react';

type LogoProps = {
  showText?: boolean;
  size?: number;
};

const Logo: React.FC<LogoProps> = ({ showText = true, size = 64 }) => {
  return (
    <div className="flex flex-col items-center justify-center">
      <svg width={size} height={size} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="MindDoc AI logo" className="mb-2">
        <defs>
          <linearGradient id="brainGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="50%" stopColor="#7C3AED" />
            <stop offset="100%" stopColor="#EC4899" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>
        
        {/* Brain shape */}
        <path d="M50 15 C35 10 25 20 25 35 C20 45 25 55 35 60 C45 65 55 65 65 60 C75 55 80 45 75 35 C75 20 65 10 50 15 Z M40 30 C38 32 36 35 38 37 C40 39 43 37 45 35 C43 33 41 31 40 30 Z M60 30 C58 32 56 35 58 37 C60 39 63 37 65 35 C63 33 61 31 60 30 Z"
              fill="url(#brainGrad)" filter="url(#glow)" />
        
        {/* Neural connections */}
        <g stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" opacity="0.8">
          <path d="M40 30 L45 35" />
          <path d="M60 30 L55 35" />
          <path d="M45 35 L55 35" />
        </g>
        
        {/* Document icon integrated */}
        <g transform="translate(35,55)">
          <rect x="0" y="0" width="30" height="20" rx="2" fill="#FFFFFF" stroke="#3B82F6" strokeWidth="1" />
          <line x1="5" y1="6" x2="25" y2="6" stroke="#3B82F6" strokeWidth="1" />
          <line x1="5" y1="10" x2="20" y2="10" stroke="#3B82F6" strokeWidth="1" />
          <line x1="5" y1="14" x2="22" y2="14" stroke="#3B82F6" strokeWidth="1" />
        </g>
      </svg>
      {showText && (
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800">MindDoc AI</h1>
          <p className="text-sm text-gray-600 mt-1">Intelligent Document Analysis & Chat</p>
        </div>
      )}
    </div>
  );
};

export default Logo;