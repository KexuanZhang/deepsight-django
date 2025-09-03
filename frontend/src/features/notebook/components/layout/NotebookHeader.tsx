import React from "react";
import { ArrowLeft, Menu, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/shared/hooks/useAuth";

interface NotebookHeaderProps {
  notebookTitle?: string;
  onMenuToggle: () => void;
  showBackButton?: boolean;
  backPath?: string;
}

/**
 * Header component for notebook pages
 * Handles navigation, menu, and logout functionality
 */
const NotebookHeader: React.FC<NotebookHeaderProps> = ({ 
  notebookTitle, 
  onMenuToggle, 
  showBackButton = true,
  backPath = "/deepdive" 
}) => {
  const navigate = useNavigate();
  const { handleLogout } = useAuth();

  return (
    <header className="flex-shrink-0 relative z-10">
      <div className="px-3 pt-4 pb-2 md:px-4 lg:px-5 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          {/* Back Button */}
          {showBackButton && (
            <button
              onClick={() => navigate(backPath)}
              className="p-2.5 rounded-xl bg-gray-100/80 hover:bg-gray-200/80 transition-all duration-200 hover:scale-105"
              title={`Back to ${backPath === "/deepdive" ? "DeepDive" : "Previous Page"}`}
            >
              <ArrowLeft className="h-5 w-5 text-gray-700" />
            </button>
          )}

          {/* Menu Toggle */}
          <button
            onClick={onMenuToggle}
            className="p-2.5 rounded-xl bg-gray-100/80 hover:bg-gray-200/80 transition-all duration-200 hover:scale-105"
          >
            <Menu className="h-5 w-5 text-gray-700" />
          </button>

          {/* Title with elegant styling */}
          {notebookTitle && (
            <div className="ml-4 flex items-center space-x-3">
              <div className="w-1 h-8 bg-gradient-to-b from-red-500 to-red-600 rounded-full"></div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-900 bg-clip-text text-transparent">
                {notebookTitle}
              </h1>
            </div>
          )}
        </div>

        {/* Logout Button */}
        <div className="flex items-center space-x-4">
          <button
            onClick={handleLogout}
            className="p-2.5 rounded-xl bg-red-50/80 hover:bg-red-100/80 text-red-600 hover:text-red-700 transition-all duration-200 hover:scale-105"
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default NotebookHeader;