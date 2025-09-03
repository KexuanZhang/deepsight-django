import React from "react";
import { Link } from "react-router-dom";
import { Menu } from "lucide-react";

const HomePage = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white">
      {/* Title with Icon */}
      <div className="flex items-center space-x-3 mb-8">
        <Menu className="h-6 w-6 text-red-600" />
        <h1 className="text-2xl font-bold text-red-600">DeepSight Portal</h1>
      </div>

      {/* Navigation Menu */}
      <nav className="flex flex-col space-y-4 text-center">
        <Link
          to="/dashboard"
          className="text-lg text-gray-800 hover:text-red-600 transition"
        >
          📊 Dashboard
        </Link>
        <Link
          to="/dataset"
          className="text-lg text-gray-800 hover:text-red-600 transition"
        >
          📁 Dataset
        </Link>
        <Link
          to="/deepdive"
          className="text-lg text-gray-800 hover:text-red-600 transition"
        >
          🔬 Deepdive
        </Link>
      </nav>
    </div>
  );
};

export default HomePage;
