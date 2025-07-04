import React, { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft } from "lucide-react";
import { Toaster } from "@/common/components/ui/toaster";
import { LAYOUT_RATIOS } from "../../config/uiConfig";
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
    <div className="h-screen bg-white flex flex-col relative overflow-hidden">
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
          className={`gap-4 p-4 flex-1 min-h-0 ${!isSourcesCollapsed ? 'grid' : 'flex'}`}
          style={!isSourcesCollapsed ? {
            gridTemplateColumns: `${LAYOUT_RATIOS.sources}fr ${LAYOUT_RATIOS.chat}fr ${LAYOUT_RATIOS.studio}fr`
          } : {}}
        >
          {/* Sources Panel */}
          {!isSourcesCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="border border-gray-200 rounded-lg overflow-auto relative min-h-0"
            >
              {React.cloneElement(sourcesPanel, {
                ref: sourcesListRef,
                onToggleCollapse: () => setIsSourcesCollapsed(true),
                isCollapsed: isSourcesCollapsed,
                onSelectionChange: handleSelectionChange
              })}
            </motion.div>
          )}

          {/* Expand Sources Button */}
          {isSourcesCollapsed && (
            <motion.button
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              onClick={() => setIsSourcesCollapsed(false)}
              className="w-12 flex-shrink-0 border border-gray-200 rounded-lg bg-white hover:bg-gray-50 hover:border-gray-300 flex items-center justify-center text-gray-400 hover:text-gray-600 transition-all duration-200 group shadow-sm hover:shadow-md"
              title="Expand Sources Panel"
            >
              <div className="group-hover:scale-110 transition-transform duration-200">
                <motion.div
                  animate={{ x: [0, 2, 0] }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                  className="text-gray-500 group-hover:text-gray-600 transition-colors duration-200"
                >
                  <ChevronLeft className="h-5 w-5 transform rotate-180" />
                </motion.div>
              </div>
            </motion.button>
          )}

          {/* Chat Panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className={`border border-gray-200 rounded-lg overflow-auto min-h-0 ${
              isSourcesCollapsed ? "flex-[0.618]" : ""
            }`}
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
            className={`border border-gray-200 rounded-lg overflow-auto min-h-0 ${
              isSourcesCollapsed ? "flex-[0.382]" : ""
            }`}
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