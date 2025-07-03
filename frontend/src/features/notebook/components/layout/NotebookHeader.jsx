import React from "react";
import { ArrowLeft, Menu, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/common/hooks/useAuth";

/**
 * Header component for notebook pages
 * Handles navigation, menu, and logout functionality
 */
const NotebookHeader = ({ 
  notebookTitle, 
  onMenuToggle, 
  showBackButton = true,
  backPath = "/deepdive" 
}) => {
  const navigate = useNavigate();
  const { handleLogout } = useAuth();

  return (
    <header className="flex-shrink-0 border-b border-gray-200 p-4 flex justify-between items-center relative z-10">
      <div className="flex items-center space-x-4">
        {/* Back Button */}
        {showBackButton && (
          <button
            onClick={() => navigate(backPath)}
            className="p-2 rounded-md hover:bg-gray-100"
            title={`Back to ${backPath === "/deepdive" ? "DeepDive" : "Previous Page"}`}
          >
            <ArrowLeft className="h-6 w-6 text-gray-700" />
          </button>
        )}

        {/* Menu Toggle */}
        <button
          onClick={onMenuToggle}
          className="p-2 rounded-md hover:bg-gray-100"
        >
          <Menu className="h-6 w-6 text-gray-700" />
        </button>

        {/* Title */}
        {notebookTitle && (
          <h1 className="text-3xl font-bold text-gray-800">
            {notebookTitle}
          </h1>
        )}
      </div>

      {/* Logout Button */}
      <div className="flex items-center space-x-4">
        <button
          onClick={handleLogout}
          className="text-gray-600 hover:text-gray-900"
          title="Logout"
        >
          <LogOut className="h-6 w-6" />
        </button>
      </div>
    </header>
  );
};

export default NotebookHeader;