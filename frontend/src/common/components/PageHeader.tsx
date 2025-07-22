// components/PageHeader.tsx
import React from "react";
import { Menu } from "lucide-react";

interface PageHeaderProps {
  title: string;
  onMenuClick: () => void;
}

export default function PageHeader({ title, onMenuClick }: PageHeaderProps) {
  return (
    <header className="border-b border-gray-200 p-4 flex items-center gap-4 relative z-10">
      <button
        onClick={onMenuClick}
        className="p-2 rounded-md hover:bg-gray-100"
      >
        <Menu className="h-6 w-6 text-gray-700" />
      </button>
      <h1 className="text-2xl font-semibold text-gray-900">{title}</h1>
    </header>
  );
}
