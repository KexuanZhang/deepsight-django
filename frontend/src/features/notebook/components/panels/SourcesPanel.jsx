import React from 'react';
import SourcesList from '../sources/SourcesList';

// Forward the ref so parent components (e.g., NotebookLayout) can access
// the imperative handle exposed by SourcesList via useImperativeHandle
const SourcesPanel = React.forwardRef((props, ref) => {
  return <SourcesList {...props} ref={ref} />;
});

export default SourcesPanel;