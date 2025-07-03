import React from "react";
import { BookOpen, Calendar, MoreVertical } from "lucide-react";

/**
 * Grid view component for displaying notebooks
 * Shows notebooks in a responsive card grid layout
 */
const NotebookGrid = ({ notebooks, onNotebookClick, formatDate }) => {
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
            <button className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-gray-100 transition-all">
              <MoreVertical className="w-4 h-4 text-gray-400" />
            </button>
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
    </div>
  );
};

export default NotebookGrid;