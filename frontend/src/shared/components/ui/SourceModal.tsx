import React, { useState, useRef } from "react";
import { Button } from "@/shared/components/ui/button";
import { UploadCloud } from "lucide-react";

interface Source {
  id: number;
  title: string;
  authors: string;
  ext: string;
  selected: boolean;
  link?: string;
}

interface SourceModalProps {
  onClose: () => void;
  onAddSources: (sources: Source[]) => void;
}

const SourceModal: React.FC<SourceModalProps> = ({ onClose, onAddSources }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [urlList, setUrlList] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...droppedFiles]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles((prev) => [...prev, ...selectedFiles]);
  };

  const handleUpload = () => {
    const timestamp = Date.now();
    const sources: Source[] = [];

    files.forEach((file, idx) => {
      const ext = file.name.split(".").pop()?.toLowerCase() || "";
      sources.push({
        id: timestamp + idx,
        title: file.name,
        authors: ext.toUpperCase(),
        ext,
        selected: false,
      });
    });

    const urls = urlList
      .split("\n")
      .map((url) => url.trim())
      .filter(Boolean);

    urls.forEach((url, idx) => {
      sources.push({
        id: timestamp + files.length + idx,
        title: url,
        link: url,
        authors: "Loading...",
        ext: "url",
        selected: false,
      });
    });

    if (sources.length > 0) {
      onAddSources(sources);
      setFiles([]);
      setUrlList("");
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg w-[460px] shadow-lg flex flex-col h-[600px]">
        <h2 className="text-lg font-semibold text-red-600 mb-6">Add Source</h2>

        {/* Content Area */}
        <div className="flex-1 space-y-6">
          {/* File Upload Section */}
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer bg-gray-50"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
          >
            <UploadCloud className="h-10 w-10 text-red-500 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-700">Upload Source</p>
            <p className="text-xs text-gray-500 mb-2">Drag and drop or click to select files</p>
            <p className="text-xs text-red-600 font-semibold">
              Supported file types: PDF, .txt, Markdown, audio (e.g., mp3)
            </p>
            <p className="text-xs text-gray-500 mt-2">
              {files.length} file{files.length !== 1 ? "s" : ""} selected
            </p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.txt,.md,.ppt,.mp3,.mp4"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>

          {/* URL Input Section */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Add Website URLs
            </label>
            <textarea
              rows={3}
              placeholder="Paste website URLs (one per line)..."
              value={urlList}
              onChange={(e) => setUrlList(e.target.value)}
              className="w-full border border-gray-300 px-3 py-2 rounded text-sm"
            />
          </div>
        </div>

        {/* Action Buttons - Sticky Bottom */}
        <div className="space-y-3 mt-6">
          <Button
            onClick={handleUpload}
            className="w-full bg-black text-white hover:bg-gray-900"
          >
            Upload
          </Button>

          <div className="text-right">
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SourceModal;
