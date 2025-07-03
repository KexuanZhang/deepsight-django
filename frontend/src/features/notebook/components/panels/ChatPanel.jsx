import React from 'react';
import Chat from '../chat/ChatPanel';

/**
 * Chat Panel - Main entry point for chat functionality
 * Follows same pattern as StudioPanel for consistency
 */
const ChatPanel = (props) => {
  return <Chat {...props} />;
};

export default ChatPanel;