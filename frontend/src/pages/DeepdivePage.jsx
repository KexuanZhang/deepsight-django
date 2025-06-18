<<<<<<< HEAD:Frontend/src/pages/DeepdivePage.jsx

import React, { useState } from "react";
=======
import React, { useState, useRef, useCallback } from "react";
>>>>>>> origin/main:frontend/src/pages/DeepdivePage.jsx
import { motion } from "framer-motion";
import { Toaster } from "@/components/ui/toaster";
import { Menu, X } from "lucide-react";
import Logo from "@/components/Logo";
import SourcesList from "@/components/SourcesList";
import ChatPanel from "@/components/ChatPanel";
import StudioPanel from "@/components/StudioPanel";
import Footer from "@/components/Footer";
import "highlight.js/styles/github.css";
import { Link } from "react-router-dom";


export default function DeepdivePage() {
  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const sourcesListRef = useRef(null);
  
  // Refs to store callbacks from each component
  const studioSelectionUpdateRef = useRef(null);
  
  // Function to handle selection changes from SourcesList
  const handleSelectionChange = useCallback(() => {
    // Notify StudioPanel to update its state
    if (studioSelectionUpdateRef.current) {
      studioSelectionUpdateRef.current();
    }
  }, []);

  return (
    <div className="min-h-screen bg-white flex flex-col relative">
      {/* Sidebar Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="w-64 bg-white shadow-xl p-6 z-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold">Menu</h2>
              <button
                onClick={() => setMenuOpen(false)}
                className="text-gray-600 hover:text-gray-900"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="space-y-4">
            <Link to="/dashboard" className="block text-gray-700 hover:text-red-600">Dashboard</Link>
            <Link to="/dataset" className="block text-gray-700 hover:text-red-600">Dataset</Link>
            <Link to="/deepdive" className="block text-red-600 font-semibold bg-gray-100 p-2 rounded">Deepdive</Link>
            </nav>
          </div>
          <div
            className="flex-1 bg-black bg-opacity-30"
            onClick={() => setMenuOpen(false)}
          />
        </div>
      )}

      {/* Header */}
      <header className="border-b border-gray-200 p-4 flex justify-between items-center relative z-10">
        <div className="flex items-center">
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="h-6 w-6 text-gray-700" />
          </button>
          <Logo />
        </div>

        {/* Language Switcher */}
        <div className="relative group">
          <div className="cursor-pointer text-gray-600 text-lg flex items-center">
            <span className="text-2xl">文A</span>
          </div>
          <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
            <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
              🇺🇸 <span className="ml-2">English</span>
            </button>
            <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
              🇨🇳 <span className="ml-2">简体中文</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-col flex-1 relative">
        <div className="flex-1">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 h-[calc(100vh-4rem)] overflow-hidden relative">
            {/* Sources Panel */}
            {!isSourcesCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className="col-span-1 md:col-span-3 border border-gray-200 rounded-lg overflow-auto relative"
              >
                <SourcesList 
                  ref={sourcesListRef} 
                  onSelectionChange={handleSelectionChange}
                />
                <button
                  onClick={() => setIsSourcesCollapsed(true)}
                  className="absolute right-[-10px] top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded shadow w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 z-50"
                  title="Collapse Sources"
                >
                  ❮
                </button>
              </motion.div>
            )}

            {/* Expand Sources Button */}
            {isSourcesCollapsed && (
              <button
                onClick={() => setIsSourcesCollapsed(false)}
                className="absolute left-0 top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded shadow w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 z-50"
                title="Expand Sources"
              >
                ❯
              </button>
            )}

            {/* Chat Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
              className={`border border-gray-200 rounded-lg overflow-auto ${
                isSourcesCollapsed ? "col-span-1 md:col-span-6" : "col-span-1 md:col-span-5"
              }`}
            >
              <ChatPanel />
            </motion.div>

            {/* Studio Panel */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.2 }}
              className={`border border-gray-200 rounded-lg overflow-auto ${
                isSourcesCollapsed ? "col-span-1 md:col-span-6" : "col-span-1 md:col-span-4"
              }`}
            >
              <StudioPanel 
                sourcesListRef={sourcesListRef} 
                onSelectionChange={(callback) => {
                  studioSelectionUpdateRef.current = callback;
                }}
              />
            </motion.div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
      <Toaster />
    </div>
  );
}
