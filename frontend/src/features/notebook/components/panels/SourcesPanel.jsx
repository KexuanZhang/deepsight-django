import React from 'react';
import SourcesList from '../sources/SourcesList';

/**
 * Sources Panel - Main entry point for sources functionality
 * Follows same pattern as StudioPanel for consistency
 */
const SourcesPanel = (props) => {
  return <SourcesList {...props} />;
};

export default SourcesPanel;