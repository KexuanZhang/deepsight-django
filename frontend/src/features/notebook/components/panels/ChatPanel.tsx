import React from 'react';
import Chat from '@/features/notebook/components/chat/ChatPanel';

interface ChatPanelProps {
  notebookId: string;
  sourcesListRef: React.RefObject<HTMLDivElement>;
  onSelectionChange?: (selection: any) => void;
}

/**
 * Chat Panel - Main entry point for chat functionality
 * Follows same pattern as StudioPanel for consistency
 */
const ChatPanel: React.FC<ChatPanelProps> = (props) => {
  return <Chat {...props} />;
};

export default ChatPanel;