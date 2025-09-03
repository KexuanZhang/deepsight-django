import React, { useState } from "react";
import { Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import { Toaster } from "@/shared/components/ui/toaster";
import Logo from "@/shared/components/common/Logo";
import Footer from "@/shared/components/common/Footer";

export default function DatasetPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white flex flex-col relative">
      {/* Sidebar Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="w-64 bg-white shadow-xl p-6 z-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold">Menu</h2>
              <button
                onClick={() => setMenuOpen(false)}
                className="text-gray-600 hover:text-gray-900"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="space-y-4">
              <Link to="/" className="block text-gray-700 hover:text-red-600">Home Page</Link>
              <Link to="/dashboard" className="block text-gray-700 hover:text-red-600">Dashboard</Link>
              <Link to="/dataset" className="block text-red-600 font-semibold bg-gray-100 p-2 rounded">Dataset</Link>
              <Link to="/deepdive" className="block text-gray-700 hover:text-red-600">Deepdive</Link>
            </nav>
          </div>
          <div
            className="flex-1 bg-black bg-opacity-30"
            onClick={() => setMenuOpen(false)}
          />
        </div>
      )}

      {/* Header */}
      <header className="border-b border-gray-200 p-4 flex justify-between items-center relative z-10">
        <div className="flex items-center">
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="h-6 w-6 text-gray-700" />
          </button>
          <Logo />
        </div>

        {/* Language Switcher */}
        <div className="relative group">
          <div className="cursor-pointer text-gray-600 text-lg flex items-center">
            <span className="text-2xl">文A</span>
          </div>
          <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
            <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
              🇺🇸 <span className="ml-2">English</span>
            </button>
            <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
              🇨🇳 <span className="ml-2">简体中文</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-6 py-8">
        <h2 className="text-2xl font-semibold text-gray-800 mb-6">Research Papers</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(9)].map((_, idx) => (
            <div
              key={idx}
              className="border border-gray-200 rounded-lg shadow-sm p-4 h-48 flex items-center justify-center text-gray-400"
            >
              Empty Paper Card
            </div>
          ))}
        </div>
      </main>

      <Footer />
      <Toaster />
    </div>
  );
}
