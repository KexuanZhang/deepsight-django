import React, { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft } from "lucide-react";
import { Toaster } from "@/common/components/ui/toaster";
import { LAYOUT_RATIOS, COLORS, SHADOWS, RESPONSIVE_PANELS } from "../../config/uiConfig";
import NotebookHeader from "./NotebookHeader";
import SidebarMenu from "./SidebarMenu";

/**
 * Layout component for notebook pages
 * Handles responsive layout with collapsible panels
 */
const NotebookLayout = ({ 
  notebookTitle,
  sourcesPanel,
  chatPanel,
  studioPanel,
  onSourcesSelectionChange 
}) => {
  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const sourcesListRef = useRef(null);
  const selectionChangeCallbackRef = useRef(null);

  // Handle selection changes from SourcesList
  const handleSelectionChange = useCallback(() => {
    if (selectionChangeCallbackRef.current) {
      selectionChangeCallbackRef.current();
    }
  }, []);
  
  // Function to register callback from panels
  const registerSelectionCallback = useCallback((callback) => {
    selectionChangeCallbackRef.current = callback;
  }, []);

  return (
    <div className="h-screen bg-gradient-to-br from-gray-500 to-gray-600 flex flex-col relative overflow-hidden">
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
          className={`${RESPONSIVE_PANELS.mobile.gap} ${RESPONSIVE_PANELS.mobile.padding} md:${RESPONSIVE_PANELS.tablet.gap} md:${RESPONSIVE_PANELS.tablet.padding} lg:${RESPONSIVE_PANELS.desktop.gap} lg:${RESPONSIVE_PANELS.desktop.padding} flex-1 min-h-0 grid`}
          style={{
            gridTemplateColumns: isSourcesCollapsed 
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
              {!isSourcesCollapsed ? (
                <motion.div
                  key="sources-content"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                >
                  {React.cloneElement(sourcesPanel, {
                    ref: sourcesListRef,
                    onToggleCollapse: () => setIsSourcesCollapsed(true),
                    isCollapsed: isSourcesCollapsed,
                    onSelectionChange: handleSelectionChange
                  })}
                </motion.div>
              ) : (
                <motion.div
                  key="expand-button"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center justify-center h-full"
                >
                  <motion.button
                    onClick={() => setIsSourcesCollapsed(false)}
                    className={`w-8 h-8 ${COLORS.panels.sources.background} backdrop-blur-sm rounded-full ${SHADOWS.panel.base} ${SHADOWS.panel.hover} flex items-center justify-center ${COLORS.panels.sources.text} ${COLORS.panels.sources.textHover} transition-all duration-300 group`}
                    title="Expand Sources Panel"
                  >
                    <div className="group-hover:scale-110 transition-transform duration-200">
                      <motion.div
                        animate={{ x: [0, 2, 0] }}
                        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                        className={`${COLORS.panels.sources.text} ${COLORS.panels.sources.textHover} transition-colors duration-200`}
                      >
                        <ChevronLeft className="h-4 w-4 transform rotate-180" />
                      </motion.div>
                    </div>
                  </motion.button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Chat Panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className={`${COLORS.panels.chat.background} backdrop-blur-sm ${RESPONSIVE_PANELS.mobile.radius} lg:${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} ${SHADOWS.panel.hover} transition-all duration-300 overflow-auto min-h-0`}
          >
            {React.cloneElement(chatPanel, {
              sourcesListRef: sourcesListRef,
              onSelectionChange: registerSelectionCallback
            })}
          </motion.div>

          {/* Studio Panel */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className={`${COLORS.panels.studio.background} backdrop-blur-sm ${RESPONSIVE_PANELS.mobile.radius} lg:${RESPONSIVE_PANELS.desktop.radius} ${SHADOWS.panel.base} ${SHADOWS.panel.hover} transition-all duration-300 overflow-auto min-h-0`}
          >
            {React.cloneElement(studioPanel, {
              sourcesListRef: sourcesListRef,
              onSelectionChange: registerSelectionCallback
            })}
          </motion.div>
        </div>
      </main>

      <Toaster />
    </div>
  );
};

export default NotebookLayout;