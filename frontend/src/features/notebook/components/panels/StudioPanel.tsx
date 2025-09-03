import React from 'react';
import Studio from "@/features/notebook/components/studio/StudioPanel";
import { FileItem, SourceItem } from "@/features/notebook/components/studio/types";

interface SourcesListRef {
  getSelectedFiles?: () => FileItem[];
  getSelectedSources?: () => SourceItem[];
}

interface StudioPanelProps {
  notebookId: string;
  sourcesListRef: React.RefObject<SourcesListRef>;
  onSelectionChange: (selection: any) => void;
  onOpenModal: (modalType: string, data?: any) => void;
  onCloseModal: (modalType: string) => void;
}

/**
 * Studio Panel - Main entry point for studio functionality
 * Entry point for consistency with other panels
 */
const StudioPanel: React.FC<StudioPanelProps> = (props) => {
  return <Studio {...props} />;
};

export default StudioPanel;