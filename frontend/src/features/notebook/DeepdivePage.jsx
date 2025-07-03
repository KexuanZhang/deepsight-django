import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useAuth } from "../../common/hooks/useAuth";
import { useNotebookData } from "./hooks/useNotebookData";
import NotebookLayout from "./components/layout/NotebookLayout";
import SourcesList from "./components/SourcesList";
import ChatPanel from "./components/ChatPanel";
import StudioPanel from "./components/studio/StudioPanel";
import "highlight.js/styles/github.css";

/**
 * DeepdivePage component
 * Uses extracted hooks and layout components following SOLID principles
 */
export default function DeepdivePage() {
  const { notebookId } = useParams();
  const { isAuthenticated, authChecked } = useAuth();
  const { 
    currentNotebook, 
    loading: loadingNotebook, 
    error: loadError,
    fetchNotebook,
    primeCsrf,
    clearError 
  } = useNotebookData();

  // Prime CSRF on mount
  useEffect(() => {
    if (authChecked && isAuthenticated) {
      primeCsrf();
    }
  }, [authChecked, isAuthenticated, primeCsrf]);

  // Fetch notebook metadata
  useEffect(() => {
    if (authChecked && isAuthenticated && notebookId) {
      fetchNotebook(notebookId);
    }
  }, [authChecked, isAuthenticated, notebookId, fetchNotebook]);

  // Loading state
  if (!authChecked || loadingNotebook) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <span className="text-gray-500">Loading notebook…</span>
      </div>
    );
  }

  // Error state
  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-white p-4">
        <p className="text-red-600 mb-4">{loadError}</p>
        <div className="space-x-4">
          <button
            onClick={() => window.history.back()}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
          >
            Go Back
          </button>
          <button
            onClick={() => {
              clearError();
              fetchNotebook(notebookId);
            }}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Main render
  return (
    <NotebookLayout
      notebookTitle={currentNotebook?.name}
      sourcesPanel={<SourcesList notebookId={notebookId} />}
      chatPanel={<ChatPanel notebookId={notebookId} />}
      studioPanel={<StudioPanel notebookId={notebookId} />}
    />
  );
}