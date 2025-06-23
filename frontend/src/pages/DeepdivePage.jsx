import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { Toaster } from "@/components/ui/toaster";
import { Menu, X, ArrowLeft, LogOut, ChevronLeft } from "lucide-react";
import Logo from "@/components/Logo";
import SourcesList from "@/components/SourcesList";
import ChatPanel from "@/components/ChatPanel";
import StudioPanel from "@/components/StudioPanel";
import "highlight.js/styles/github.css";
import { Link, useParams, useNavigate } from "react-router-dom";

// helper to read CSRF token from cookies
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export default function DeepdivePage() {
  const { notebookId } = useParams();
  const navigate       = useNavigate();

  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // Refs and handlers for component communication
  const sourcesListRef = useRef(null);
  const selectionChangeCallbackRef = useRef(null);
  
  // Handle selection changes from SourcesList
  const handleSelectionChange = useCallback(() => {
    if (selectionChangeCallbackRef.current) {
      selectionChangeCallbackRef.current();
    }
  }, []);
  
  // Function to register callback from StudioPanel
  const registerSelectionCallback = useCallback((callback) => {
    selectionChangeCallbackRef.current = callback;
  }, []);

  const [notebookMeta, setNotebookMeta] = useState(null);
  const [loadingNotebook, setLoadingNotebook] = useState(true);
  const [loadError, setLoadError] = useState("");

  // prime CSRF on mount
  useEffect(() => {
    fetch("/api/users/csrf/", {
      method: "GET",
      credentials: "include",
    }).catch(() => {});
  }, []);

  // fetch notebook metadata
  useEffect(() => {
    async function fetchMeta() {
      setLoadingNotebook(true);
      setLoadError("");

      try {
        const res = await fetch(`/api/v1/notebooks/${notebookId}/`, {
          credentials: "include",
        });

        if (res.status === 401) {
          navigate("/login");
          return;
        }
        if (res.status === 404) {
          setLoadError("Notebook not found.");
          return;
        }
        if (!res.ok) {
          throw new Error("Failed to load notebook data.");
        }

        const data = await res.json();
        setNotebookMeta(data);
      } catch (e) {
        console.error(e);
        setLoadError("Could not load notebook data.");
      } finally {
        setLoadingNotebook(false);
      }
    }

    fetchMeta();
  }, [notebookId, navigate]);

  if (loadingNotebook) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <span className="text-gray-500">Loading notebook…</span>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-white p-4">
        <p className="text-red-600 mb-4">{loadError}</p>
        <button
          onClick={() => navigate("/deepdive")}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Back to Notebooks
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen bg-white flex flex-col relative overflow-hidden">
      {/* Sidebar Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="w-64 bg-white shadow-xl p-6 z-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold">Menu</h2>
              <button onClick={() => setMenuOpen(false)}>
                <X className="h-5 w-5 text-gray-600 hover:text-gray-900" />
              </button>
            </div>
            <nav className="space-y-4">
              <Link to="/"        className="block text-gray-700 hover:text-red-600">Home Page</Link>
              <Link to="/dashboard" className="block text-gray-700 hover:text-red-600">Dashboard</Link>
              <Link to="/dataset"   className="block text-gray-700 hover:text-red-600">Dataset</Link>
              <Link to="/deepdive"  className="block text-red-600 font-semibold bg-gray-100 p-2 rounded">Notebooks</Link>
            </nav>
          </div>
          <div
            className="flex-1 bg-black bg-opacity-30"
            onClick={() => setMenuOpen(false)}
          />
        </div>
      )}

      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200 p-4 flex justify-between items-center relative z-10">
        <div className="flex items-center space-x-4">
          {/* Back Button */}
          <button
            onClick={() => navigate("/deepdive")}
            className="p-2 rounded-md hover:bg-gray-100"
            title="Back to Notebooks"
          >
            <ArrowLeft className="h-6 w-6 text-gray-700" />
          </button>

          {/* Menu Toggle */}
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="h-6 w-6 text-gray-700" />
          </button>

          {/* Logo & Title */}
          <Logo />
          <h2 className="text-xl font-semibold ml-4">
            {notebookMeta.name}
          </h2>
        </div>

        {/* Logout */}
        <div className="flex items-center space-x-4">
          <button
            onClick={async () => {
              await fetch("/api/users/logout/", {
                method: "POST",
                credentials: "include",
                headers: { "X-CSRFToken": getCookie("csrftoken") },
              });
              navigate("/login");
            }}
            className="text-gray-600 hover:text-gray-900"
            title="Logout"
          >
            <LogOut className="h-6 w-6" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-0">
        <div className={`flex gap-4 p-4 flex-1 min-h-0 ${!isSourcesCollapsed ? 'md:grid md:grid-cols-12' : ''}`}>
          {/* Sources Panel */}
          {!isSourcesCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="col-span-1 md:col-span-3 border border-gray-200 rounded-lg overflow-auto relative min-h-0"
            >
              <SourcesList 
                ref={sourcesListRef}
                notebookId={notebookId} 
                onToggleCollapse={() => setIsSourcesCollapsed(true)}
                isCollapsed={isSourcesCollapsed}
                onSelectionChange={handleSelectionChange}
              />
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
              isSourcesCollapsed ? "flex-1" : "col-span-1 md:col-span-5"
            }`}
          >
            <ChatPanel notebookId={notebookId} />
          </motion.div>

          {/* Studio Panel */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className={`border border-gray-200 rounded-lg overflow-auto min-h-0 ${
              isSourcesCollapsed ? "flex-1" : "col-span-1 md:col-span-4"
            }`}
          >
            <StudioPanel 
              notebookId={notebookId} 
              sourcesListRef={sourcesListRef}
              onSelectionChange={registerSelectionCallback}
            />
          </motion.div>
        </div>
        
        {/* Copyright Footer */}
        <div className="flex-shrink-0 p-4 text-center text-sm text-gray-500 border-t border-gray-100">
          © 2025, Huawei. All Rights Reserved.
        </div>
      </main>

      <Toaster />
    </div>
  );
}
