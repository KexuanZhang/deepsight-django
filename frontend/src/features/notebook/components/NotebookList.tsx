import React, { useState, useEffect } from "react";
import { BookOpen, Calendar, Edit3, ChevronDown, Trash2, MoreVertical } from "lucide-react";

interface Notebook {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface NotebookListProps {
  notebooks: Notebook[];
  onNotebookClick: (notebook: Notebook) => void;
  onDeleteNotebook: (notebookId: string) => Promise<void>;
  formatDate: (date: string) => string;
}

/**
 * List view component for displaying notebooks
 * Shows notebooks in a detailed list format
 */
const NotebookList: React.FC<NotebookListProps> = ({ notebooks, onNotebookClick, onDeleteNotebook, formatDate }) => {
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
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="divide-y divide-gray-100">
        {notebooks.map((notebook) => (
          <div
            key={notebook.id}
            onClick={() => onNotebookClick(notebook)}
            className="group p-6 hover:bg-gray-50 cursor-pointer transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4 flex-1">
                <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 group-hover:text-red-600 transition-colors">
                    {notebook.name}
                  </h3>
                  {notebook.description && (
                    <p className="text-gray-600 text-sm mt-1 truncate">
                      {notebook.description}
                    </p>
                  )}
                  <div className="flex items-center text-xs text-gray-500 mt-2 space-x-4">
                    <div className="flex items-center space-x-1">
                      <Calendar className="w-3 h-3" />
                      <span>Created {formatDate(notebook.created_at)}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
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
                <ChevronDown className="w-5 h-5 text-gray-400 rotate-90 group-hover:text-red-500 transition-colors" />
              </div>
            </div>
          </div>
        ))}
      </div>
      
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

export default NotebookList;