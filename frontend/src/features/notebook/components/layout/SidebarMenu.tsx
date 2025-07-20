import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { Link } from "react-router-dom";

interface SidebarMenuProps {
  isOpen: boolean;
  onClose: () => void;
  currentPath?: string;
}

/**
 * Reusable sidebar menu component
 * Displays navigation links with overlay
 */
const SidebarMenu: React.FC<SidebarMenuProps> = ({ isOpen, onClose, currentPath = "/deepdive" }) => {
  const menuItems = [
    { path: "/", label: "Home Page" },
    { path: "/dashboard", label: "Dashboard" },
    { path: "/dataset", label: "Dataset" },
    { path: "/deepdive", label: "DeepDive" }
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex">
          <motion.div
            initial={{ x: -300 }}
            animate={{ x: 0 }}
            exit={{ x: -300 }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="w-64 bg-white shadow-xl p-6 z-50"
          >
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold">Menu</h2>
              <button onClick={onClose}>
                <X className="h-5 w-5 text-gray-600 hover:text-gray-900" />
              </button>
            </div>
            <nav className="space-y-4">
              {menuItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`block text-gray-700 hover:text-red-600 ${
                    currentPath === item.path 
                      ? "text-red-600 font-semibold bg-gray-100 p-2 rounded" 
                      : ""
                  }`}
                  onClick={onClose}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </motion.div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 bg-black bg-opacity-30"
            onClick={onClose}
          />
        </div>
      )}
    </AnimatePresence>
  );
};

export default SidebarMenu;