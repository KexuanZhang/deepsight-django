import React, { useState, useEffect } from "react";
import { BookOpen, Calendar, MoreVertical, Trash2 } from "lucide-react";

interface Notebook {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface NotebookGridProps {
  notebooks: Notebook[];
  onNotebookClick: (notebook: Notebook) => void;
  onDeleteNotebook: (notebookId: string) => Promise<void>;
  formatDate: (date: string) => string;
}

/**
 * Grid view component for displaying notebooks
 * Shows notebooks in a responsive card grid layout
 */
const NotebookGrid: React.FC<NotebookGridProps> = ({ notebooks, onNotebookClick, onDeleteNotebook, formatDate }) => {
  const [showDeleteDialog, setShowDeleteDialog] = useState<Notebook | null>(null);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, notebook: Notebook) => {
    e.stopPropagation();
    setShowDeleteDialog(notebook);
    setOpenDropdown(null);
  };

  const handleConfirmDelete = async () => {
    if (showDeleteDialog) {
      await onDeleteNotebook(showDeleteDialog.id);
      setShowDeleteDialog(null);
    }
  };

  const handleCancelDelete = () => {
    setShowDeleteDialog(null);
  };

  const handleDropdownClick = (e: React.MouseEvent, notebookId: string) => {
    e.stopPropagation();
    setOpenDropdown(openDropdown === notebookId ? null : notebookId);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setOpenDropdown(null);
    };
    if (openDropdown) {
      document.addEventListener('click', handleClickOutside);
    }
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [openDropdown]);
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {notebooks.map((notebook) => (
        <div
          key={notebook.id}
          onClick={() => onNotebookClick(notebook)}
          className="group bg-white rounded-2xl border border-gray-200 hover:border-red-300 p-6 cursor-pointer transition-all duration-200 hover:shadow-xl hover:-translate-y-1"
        >
          <div className="flex items-start justify-between mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div className="relative">
              <button
                onClick={(e) => handleDropdownClick(e, notebook.id)}
                className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-gray-100 transition-all"
              >
                <MoreVertical className="w-4 h-4 text-gray-400" />
              </button>
              
              {openDropdown === notebook.id && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                  <div className="py-1">
                    <button
                      onClick={(e) => handleDeleteClick(e, notebook)}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      <span>Delete notebook</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-red-600 transition-colors">
            {notebook.name}
          </h3>
          
          {notebook.description && (
            <p className="text-gray-600 text-sm mb-4 line-clamp-2">
              {notebook.description}
            </p>
          )}
          
          <div className="flex items-center text-xs text-gray-500 space-x-4">
            <div className="flex items-center space-x-1">
              <Calendar className="w-3 h-3" />
              <span>{formatDate(notebook.created_at)}</span>
            </div>
          </div>
        </div>
      ))}
      
      {showDeleteDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete Notebook</h3>
            <p className="text-gray-600 mb-4">
              Are you sure you want to delete "{showDeleteDialog.name}"? This action cannot be undone and will delete all associated data including reports and podcasts.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={handleCancelDelete}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotebookGrid;