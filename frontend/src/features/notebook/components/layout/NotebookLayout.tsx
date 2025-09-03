import React, { useState, useRef, useCallback, ReactElement } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, Database, RectangleHorizontal } from "lucide-react";
import { Toaster } from "@/shared/components/ui/toaster";
import { Button } from "@/shared/components/ui/button";
import { LAYOUT_RATIOS, COLORS, SHADOWS, RESPONSIVE_PANELS, PANEL_HEADERS } from "@/features/notebook/config/uiConfig";
import NotebookHeader from "@/features/notebook/components/layout/NotebookHeader";
import SidebarMenu from "@/features/notebook/components/layout/SidebarMenu";

interface ModalState {
  isOpen: boolean;
  data: ReactElement | null;
}

interface ModalsState {
  filePreview: ModalState;
  uploadModal: ModalState;
  addSourceModal: ModalState;
  advancedSettings: ModalState;
  gallerySettings: ModalState;
  customizeReport: ModalState;
  customizePodcast: ModalState;
}

interface NotebookLayoutProps {
  notebookTitle?: string;
  sourcesPanel: ReactElement;
  chatPanel: ReactElement;
  studioPanel: ReactElement;
  onSourcesSelectionChange?: () => void;
  sourcesRemovedTrigger?: number;
}

/**
 * Layout component for notebook pages
 * Handles responsive layout with collapsible panels and global modal management
 */
const NotebookLayout: React.FC<NotebookLayoutProps> = ({ 
  notebookTitle,
  sourcesPanel,
  chatPanel,
  studioPanel,
  onSourcesSelectionChange,
  sourcesRemovedTrigger
}) => {
  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [isStudioExpanded, setIsStudioExpanded] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const sourcesListRef = useRef<any>(null);
  const selectionChangeCallbackRef = useRef<(() => void) | null>(null);

  // Modal state management
  const [modals, setModals] = useState<ModalsState>({
    filePreview: { isOpen: false, data: null },
    uploadModal: { isOpen: false, data: null },
    addSourceModal: { isOpen: false, data: null },
    advancedSettings: { isOpen: false, data: null },
    gallerySettings: { isOpen: false, data: null },
    customizeReport: { isOpen: false, data: null },
    customizePodcast: { isOpen: false, data: null }
  });

  // Handle selection changes from SourcesList
  const handleSelectionChange = useCallback(() => {
    if (selectionChangeCallbackRef.current) {
      selectionChangeCallbackRef.current();
    }
  }, []);
  
  // Function to register callback from panels
  const registerSelectionCallback = useCallback((callback: () => void) => {
    selectionChangeCallbackRef.current = callback;
  }, []);

  // Modal management functions
  const openModal = useCallback((modalType: keyof ModalsState, data: ReactElement | null = null) => {
    setModals(prev => ({
      ...prev,
      [modalType]: { isOpen: true, data }
    }));
  }, []);

  const closeModal = useCallback((modalType: keyof ModalsState) => {
    setModals(prev => ({
      ...prev,
      [modalType]: { isOpen: false, data: null }
    }));
  }, []);

  // Handle studio expand/collapse
  const handleStudioToggleExpand = useCallback(() => {
    setIsStudioExpanded(prev => !prev);
  }, []);

  // Pass modal functions to panels
  const panelProps = {
    sourcesListRef,
    onSelectionChange: registerSelectionCallback,
    onOpenModal: openModal,
    onCloseModal: closeModal,
    sourcesRemovedTrigger
  };

  return (
    <div className="h-screen bg-gradient-to-br from-gray-200 to-gray-300 flex flex-col relative overflow-hidden">
      {/* Sidebar Menu */}
      <SidebarMenu 
        isOpen={menuOpen} 
        onClose={() => setMenuOpen(false)}
        currentPath="/deepdive"
      />

      {/* Header */}
      <NotebookHeader 
        notebookTitle={notebookTitle}
        onMenuToggle={() => setMenuOpen(true)}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-0">
        <div 
          className={`${RESPONSIVE_PANELS.mobile.gap} ${RESPONSIVE_PANELS.mobile.padding} md:${RESPONSIVE_PANELS.tablet.gap} md:${RESPONSIVE_PANELS.tablet.padding} lg:${RESPONSIVE_PANELS.desktop.gap} lg:${RESPONSIVE_PANELS.desktop.padding} flex-1 min-h-0 grid transition-all duration-300`}
          style={{
            gridTemplateColumns: isStudioExpanded 
              ? `40px 4fr 8fr` // Studio expanded: keep collapsed sources bar visible, smaller chat, larger studio
              : isSourcesCollapsed 
                ? `40px ${LAYOUT_RATIOS.chat}fr ${LAYOUT_RATIOS.studio}fr`
                : `${LAYOUT_RATIOS.sources}fr ${LAYOUT_RATIOS.chat}fr ${LAYOUT_RATIOS.studio}fr`
          }}
        >
          {/* Sources Panel */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ 
              opacity: 1, 
              x: 0
            }}
            transition={{ duration: 0.3 }}
            className={`${COLORS.panels.sources.background} backdrop-blur-sm ${RESPONSIVE_PANELS.mobile.radius} lg:${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} ${SHADOWS.panel.hover} transition-all duration-300 overflow-hidden min-h-0 relative`}
          >
            <AnimatePresence mode="wait">
              {!isSourcesCollapsed && !isStudioExpanded ? (
                <motion.div
                  key="sources-content"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20, transition: { duration: 0.15 } }}
                  transition={{ duration: 0.15 }}
                >
                  {React.cloneElement(sourcesPanel, {
                    ...panelProps,
                    ref: sourcesListRef,
                    onToggleCollapse: () => setIsSourcesCollapsed(true),
                    isCollapsed: isSourcesCollapsed,
                    onSelectionChange: handleSelectionChange
                  })}
                </motion.div>
              ) : (
                <motion.div
                  key="collapsed-sources"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, transition: { duration: 0.15 } }}
                  transition={{ duration: 0.15 }}
                  className="h-full flex flex-col"
                >
                  {/* Collapsed Header - Entire bar clickable with red highlight */}
                  <div 
                    className="flex-shrink-0 py-4 bg-gray-100/95 backdrop-blur-sm flex items-center justify-center h-full w-full cursor-pointer hover:bg-red-50 transition-all duration-200 group"
                    onClick={() => {
                      if (isStudioExpanded) {
                        setIsStudioExpanded(false);
                      }
                      setIsSourcesCollapsed(false);
                    }}
                    title={isStudioExpanded ? "Minimize Studio & Expand Sources Panel" : "Expand Sources Panel"}
                  >
                    <Database className="h-4 w-4 text-gray-400 group-hover:text-red-600 transition-all duration-200" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Chat Panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className={`${COLORS.panels.chat.background} backdrop-blur-sm ${RESPONSIVE_PANELS.mobile.radius} lg:${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} ${SHADOWS.panel.hover} transition-all duration-300 overflow-hidden min-h-0`}
          >
            {React.cloneElement(chatPanel, panelProps)}
          </motion.div>

          {/* Studio Panel */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className={`${COLORS.panels.studio.background} backdrop-blur-sm ${RESPONSIVE_PANELS.mobile.radius} lg:${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} ${SHADOWS.panel.hover} transition-all duration-300 overflow-auto min-h-0`}
          >
            {React.cloneElement(studioPanel, {
              ...panelProps,
              onToggleExpand: handleStudioToggleExpand,
              isStudioExpanded: isStudioExpanded
            })}
          </motion.div>
        </div>
      </main>

      {/* Global Modals - Rendered at top level with high z-index */}
      <AnimatePresence>
        {/* File Preview Modal */}
        {modals.filePreview.isOpen && modals.filePreview.data && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999] p-4"
            onClick={() => closeModal('filePreview')}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.3 }}
              className="bg-white rounded-xl shadow-xl max-w-5xl w-full max-h-[95vh] overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.filePreview.data}
            </motion.div>
          </motion.div>
        )}

        {/* Upload Modal */}
        {modals.uploadModal.isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-[9999] p-4"
            onClick={() => closeModal('uploadModal')}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.5 }}
              className="bg-gray-900 rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.uploadModal.data}
            </motion.div>
          </motion.div>
        )}

        {/* Add Source Modal */}
        {modals.addSourceModal.isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999] p-4"
            onClick={() => closeModal('addSourceModal')}
          >
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ duration: 0.15 }}
              className="bg-white rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto scrollbar-hide shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.addSourceModal.data}
            </motion.div>
          </motion.div>
        )}

        {/* Advanced Settings Modal */}
        {modals.advancedSettings.isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-black/50 flex items-center justify-center p-4"
            onClick={() => closeModal('advancedSettings')}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.3 }}
              className="bg-white p-6 rounded-xl w-full max-w-4xl shadow-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.advancedSettings.data}
            </motion.div>
          </motion.div>
        )}

        {/* Gallery Settings Modal */}
        {modals.gallerySettings.isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-black/40 flex items-center justify-center"
            onClick={() => closeModal('gallerySettings')}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.3 }}
              className="bg-white rounded-lg shadow-lg w-96 p-6"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.gallerySettings.data}
            </motion.div>
          </motion.div>
        )}

        {/* Customize Report Modal */}
        {modals.customizeReport.isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-black/50 flex items-center justify-center p-4"
            onClick={() => closeModal('customizeReport')}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.3 }}
              className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.customizeReport.data}
            </motion.div>
          </motion.div>
        )}

        {/* Customize Podcast Modal */}
        {modals.customizePodcast.isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[9999] bg-black/50 flex items-center justify-center p-4"
            onClick={() => closeModal('customizePodcast')}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ type: "spring", duration: 0.3 }}
              className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {modals.customizePodcast.data}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <Toaster />
    </div>
  );
};

export default NotebookLayout;