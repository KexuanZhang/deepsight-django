import React, { useState, useRef } from "react";
import { Button } from "@/common/components/ui/button";
import { UploadCloud } from "lucide-react";
import { VALIDATION_CONFIG } from "@/features/notebook/config/fileConfig";

const SourceModal = ({ onClose, onAddSources }) => {
  const [files, setFiles] = useState([]);
  const [urlList, setUrlList] = useState("");
  const fileInputRef = useRef();

  const handleFileDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles((prev) => [...prev, ...droppedFiles]);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...selectedFiles]);
  };

  const handleUpload = () => {
    const timestamp = Date.now();
    const sources = [];

    files.forEach((file, idx) => {
      const ext = file.name.split(".").pop().toLowerCase();
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
      <div className="bg-white p-6 rounded-lg w-[460px] shadow-lg space-y-6">
        <h2 className="text-lg font-semibold text-red-600">Add Source</h2>

        {/* File Upload Section */}
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer bg-gray-50"
          onClick={() => fileInputRef.current.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
        >
          <UploadCloud className="h-10 w-10 text-red-500 mx-auto mb-2" />
          <p className="text-sm font-medium text-gray-700">Upload Source</p>
          <p className="text-xs text-gray-500 mb-2">Drag and drop or click to select files</p>
          <p className="text-xs text-red-600 font-semibold">
            Supported file types: PDF, .txt, Markdown, PPTX, DOCX, Audio, Video
          </p>
          <p className="text-xs text-gray-500 mt-2">
            {files.length} file{files.length !== 1 ? "s" : ""} selected
          </p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={VALIDATION_CONFIG.acceptString}
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

        {/* Action Buttons */}
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
  );
};

export default SourceModal;
