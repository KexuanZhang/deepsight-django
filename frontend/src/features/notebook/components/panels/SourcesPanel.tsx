import React from 'react';
import SourcesList from "@/features/notebook/components/sources/SourcesList";
import { SourcesListProps } from "@/features/notebook/type";

// Define the SourcesListRef interface to match what SourcesList exposes
interface SourcesListRef {
  getSelectedFiles: () => any[];
  getSelectedSources: () => any[];
  clearSelection: () => void;
  refreshSources: () => Promise<void>;
  startUploadTracking: (uploadFileId: string) => void;
  onProcessingComplete: (completedUploadId?: string) => void;
}

// Forward the ref so parent components (e.g., NotebookLayout) can access
// the imperative handle exposed by SourcesList via useImperativeHandle
const SourcesPanel = React.forwardRef<SourcesListRef, SourcesListProps>((props, ref) => {
  return <SourcesList {...props} ref={ref} />;
});

export default SourcesPanel;