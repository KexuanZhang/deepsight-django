import React from 'react';
import Studio from '../studio/StudioPanel';

/**
 * Studio Panel - Main entry point for studio functionality
 * Entry point for consistency with other panels
 */
const StudioPanel = (props) => {
  return <Studio {...props} />;
};

export default StudioPanel;