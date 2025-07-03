import React from "react";
import { BookOpen, Calendar, Edit3, ChevronDown } from "lucide-react";

/**
 * List view component for displaying notebooks
 * Shows notebooks in a detailed list format
 */
const NotebookList = ({ notebooks, onNotebookClick, formatDate }) => {
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
                <button className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-gray-200 transition-all">
                  <Edit3 className="w-4 h-4 text-gray-400" />
                </button>
                <ChevronDown className="w-5 h-5 text-gray-400 rotate-90 group-hover:text-red-500 transition-colors" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default NotebookList;