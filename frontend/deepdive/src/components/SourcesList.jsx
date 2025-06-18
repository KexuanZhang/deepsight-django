import React, {
  useState,
  useRef,
  useImperativeHandle,
  forwardRef,
  useEffect,
  useCallback
} from "react";
import {
  ArrowUpDown,
  Trash2,
  Plus,
  ChevronLeft,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  X,
  Upload,
  Link2,
  FileText,
  Globe,
  Youtube
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import apiService from "@/lib/api";

const fileIcons = {
  pdf: "📄",
  txt: "📃",
  md: "📝",
  ppt: "📊",
  pptx: "📊",
  mp3: "🎵",
  mp4: "🎞️"
};

const statusConfig = {
  pending: {
    icon: Clock,
    color: "text-yellow-500",
    bg: "bg-yellow-50",
    label: "Queued"
  },
  parsing: {
    icon: RefreshCw,
    color: "text-blue-500",
    bg: "bg-blue-50",
    label: "Processing",
    animate: true
  },
  completed: {
    icon: CheckCircle,
    color: "text-green-500",
    bg: "bg-green-50",
    label: "Completed"
  },
  error: {
    icon: AlertCircle,
    color: "text-red-500",
    bg: "bg-red-50",
    label: "Failed"
  },
  cancelled: {
    icon: X,
    color: "text-gray-500",
    bg: "bg-gray-50",
    label: "Cancelled"
  },
  unsupported: {
    icon: AlertCircle,
    color: "text-orange-500",
    bg: "bg-orange-50",
    label: "Unsupported"
  }
};


const SourcesList = forwardRef(
  ({ notebookId, onSelectionChange, ...props }, ref) => {
    const [sources, setSources] = useState([]);
    const [isHidden, setIsHidden] = useState(false);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState({});
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [isDragOver, setIsDragOver] = useState(false);
    const [linkUrl, setLinkUrl] = useState("");
    const [pasteText, setPasteText] = useState("");
    const [activeTab, setActiveTab] = useState("file");
    const sseRef = useRef(new Map());
    const fileInputRef = useRef(null);

    // SSE connections for status updates
    const sseConnectionsRef = useRef(new Map());

    const loadParsedFiles = useCallback(async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiService.listParsedFiles(notebookId);
        if (!response.success) throw new Error(response.error || "Failed to load files");

        const parsedSources = response.data.map(m => ({
          id:              m.file_id,
          title:           m.original_filename,
          authors:         generateFileDescription(m),
          ext:             m.file_extension?.substring(1) || "unknown",
          selected:        false,
          type:            "parsed",
          file_id:         m.file_id,
          upload_file_id:  m.upload_file_id,
          parsing_status:  m.parsing_status,
          metadata:        m,
          error_message:   m.error_message
        }));

        setSources(parsedSources);
      } catch (e) {
        console.error("Error loading parsed files:", e);
        setError(`Failed to load files: ${e.message}`);
        setSources([]);
      } finally {
        setIsLoading(false);
      }
    }, [notebookId]);

    useEffect(() => {
      loadParsedFiles();
      return () => {
        // teardown in-flight SSE streams
        sseConnectionsRef.current.forEach(es => es.close());
        sseConnectionsRef.current.clear();
      };
    }, [loadParsedFiles]);


    const generateFileDescription = m => {
      const size   = m.file_size   ? `${(m.file_size/(1024*1024)).toFixed(1)} MB`
                    : m.content_length ? `${(m.content_length/1000).toFixed(1)}k chars`
                    : "Unknown size";
      const status = statusConfig[m.parsing_status]?.label || m.parsing_status;
      const ext    = m.file_extension?.toUpperCase().replace(".", "") || "Unknown";
      return `${ext} • ${size} • ${status}`;
    };

    const startStatusMonitoring = useCallback((uploadFileId, sourceId) => {
      if (sseConnectionsRef.current.has(uploadFileId)) return;

      const onMessage = data => {
        const { status, job_details } = data;

        // update progress bar
        if (job_details?.progress_percentage != null) {
          setUploadProgress(p => ({
            ...p,
            [uploadFileId]: job_details.progress_percentage
          }));
        }

        // update the source entry
        setSources(prev =>
          prev.map(src =>
            src.id === sourceId
              ? {
                  ...src,
                  parsing_status: status,
                  authors: generateFileDescription({
                    ...src.metadata,
                    parsing_status: status,
                    content_length: job_details.result?.content_length || src.metadata.content_length
                  }),
                  metadata: job_details.result?.metadata || src.metadata,
                  error_message: job_details.error
                }
              : src
          )
        );

        // close stream once done
        if (["completed","error","cancelled","unsupported"].includes(status)) {
          const es = sseConnectionsRef.current.get(uploadFileId);
          es?.close();
          sseConnectionsRef.current.delete(uploadFileId);
          setUploadProgress(p => {
            const clone = {...p};
            delete clone[uploadFileId];
            return clone;
          });
          if (status === "completed") setTimeout(loadParsedFiles, 1000);
        }
      };

      const onError = err => {
        console.error("SSE error:", err);
        const es = sseConnectionsRef.current.get(uploadFileId);
        es?.close();
        sseConnectionsRef.current.delete(uploadFileId);

        setSources(prev =>
          prev.map(src =>
            src.id === sourceId
              ? {
                  ...src,
                  parsing_status: "error",
                  authors: src.authors.replace(/Processing|Queued/, "Connection Failed"),
                  error_message: "Lost connection to server during processing"
                }
              : src
          )
        );
        setUploadProgress(p => {
          const clone = {...p};
          delete clone[uploadFileId];
          return clone;
        });
      };

      // create the EventSource (note the extra notebookId arg!)
      const es = apiService.createParsingStatusStream(
        uploadFileId,
        notebookId,
        onMessage,
        onError,
        () => { sseConnectionsRef.current.delete(uploadFileId); }
      );
      sseConnectionsRef.current.set(uploadFileId, es);
    }, [loadParsedFiles, notebookId]);

    // Expose methods to parent
    // expose controls to parent
    useImperativeHandle(ref, () => ({
      getSelectedFiles:   () => sources.filter(s => s.selected && (s.file_id||s.file) && s.parsing_status==="completed"),
      getSelectedSources: () => sources.filter(s => s.selected),
      clearSelection:     () => setSources(prev => prev.map(s => ({...s,selected:false}))),
      refreshSources:     loadParsedFiles
    }));

    const toggleSource = (id) => {
      setSources((prev) =>
        prev.map((s) => (s.id === id ? { ...s, selected: !s.selected } : s))
      );
      if (onSelectionChange) setTimeout(onSelectionChange, 0);
    };

    const handleDeleteSelected = async () => {
      const toDelete = sources.filter((s) => s.selected);
      if (!toDelete.length) return;
      if (!confirm(`Delete ${toDelete.length} file(s)?`)) return;

      const results = [];
      for (const src of toDelete) {
        try {
          let res;
          if (src.upload_file_id) {
            res = await apiService.deleteFileByUploadId(src.upload_file_id);
            sseConnectionsRef.current.get(src.upload_file_id)?.close();
          } else {
            res = await apiService.deleteParsedFile(src.file_id);
          }
          if (res.success) results.push(src.id);
        } catch {}
      }
      setSources((prev) => prev.filter((s) => !results.includes(s.id)));
      await loadParsedFiles();
    };

    const selectedCount = sources.filter((s) => s.selected).length;

    const handleAddSource = () => {
      setShowUploadModal(true);
      setActiveTab("file");
      setLinkUrl("");
      setPasteText("");
    };

    // File validation
    const validateFile = (file) => {
      const allowed = ["pdf", "txt", "md", "ppt", "pptx", "mp3", "mp4"];
      const ext = file.name.split(".").pop().toLowerCase();
      const errors = [];
      const warnings = [];
      if (!ext) errors.push("No extension");
      else if (!allowed.includes(ext))
        errors.push(`.${ext} not supported`);
      if (file.size > 100 * 1024 * 1024)
        errors.push("Exceeds 100MB");
      if (file.size < 100) warnings.push("Very small");
      if (/[<>:"|?*]/.test(file.name))
        errors.push("Invalid characters");
      return {
        valid: !errors.length,
        errors,
        warnings,
        extension: ext
      };
    };

    // Core file upload handler
    const handleFileChangeInternal = async e => {
      const file = e.target.files?.[0];
      if (!file) return;

      const v = validateFile(file);
      if (!v.valid) {
        setError(`Validation failed: ${v.errors.join(", ")}`);
        return;
      }
      setError(null);

      const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2,9)}`;
      const newSrc = {
        id:             Date.now(),
        upload_file_id: uploadId,
        title:          file.name,
        authors:        `${v.extension.toUpperCase()} • ${(file.size/(1024*1024)).toFixed(1)} MB • Uploading...`,
        ext:            v.extension,
        selected:       false,
        type:           "uploading",
        file,
        parsing_status: "pending",
        metadata: {
          original_filename: file.name,
          file_extension:    `.${v.extension}`,
          file_size:         file.size
        }
      };
      setSources(prev => [...prev,newSrc]);
      setUploadProgress(p => ({ ...p, [uploadId]: 0 }));

      try {
        setUploadProgress(p => ({ ...p, [uploadId]: 10 }));
        // <— note the extra notebookId argument here!
        const resp = await apiService.parseFile(file, uploadId, notebookId);
        if (!resp.success) throw new Error(resp.error||"Upload failed");
        const data = resp.data;

        setSources(prev =>
          prev.map(s =>
            s.id === newSrc.id
              ? {
                  ...s,
                  file_id:        data.file_id,
                  type:           "parsing",
                  parsing_status: data.status,
                  authors:        `${v.extension.toUpperCase()} • ${(data.file_size/(1024*1024)).toFixed(1)} MB • ${statusConfig[data.status]?.label||data.status}`,
                  metadata:       {...s.metadata, file_size: data.file_size, file_extension: data.file_extension}
                }
              : s
          )
        );

        startStatusMonitoring(uploadId, newSrc.id);
        setTimeout(loadParsedFiles, 500);

      } catch (err) {
        console.error(err);
        setSources(prev =>
          prev.map(s =>
            s.id === newSrc.id
              ? {
                  ...s,
                  parsing_status: "error",
                  authors:        `${v.extension.toUpperCase()} • Upload failed`,
                  error_message:  err.message
                }
              : s
          )
        );
        setUploadProgress(p => {
          const clone = {...p};
          delete clone[uploadId];
          return clone;
        });
        setError(`Failed to upload ${file.name}: ${err.message}`);
      }

      e.target.value = "";
    };

    // Drag & drop
    const handleDragEnter = (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(true);
    };
    const handleDragLeave = (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
    };
    const handleDragOver = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };
    const handleDrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      if (e.dataTransfer.files.length) {
        handleFileChangeInternal({ target: { files: [e.dataTransfer.files[0]] } });
      }
    };

    // Link upload
    const handleLinkUpload = async () => {
      if (!linkUrl.trim()) {
        setError("Enter a URL");
        return;
      }
      setError(null);
      setShowUploadModal(false);
      const uploadId = `link_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const isYouTube =
        linkUrl.includes("youtube.com") || linkUrl.includes("youtu.be");
      const linkType = isYouTube ? "YouTube" : "Website";
      const newSrc = {
        id: Date.now(),
        upload_file_id: uploadId,
        title: linkUrl,
        authors: `${linkType} • Link • Processing...`,
        ext: "link",
        selected: false,
        type: "uploading",
        parsing_status: "pending",
        metadata: {
          original_filename: linkUrl,
          file_extension: ".url",
          source_type: "link"
        }
      };
      setSources((p) => [...p, newSrc]);
      setUploadProgress((p) => ({ ...p, [uploadId]: 0 }));
      setUploadProgress((p) => ({ ...p, [uploadId]: 20 }));

      // simulate
      setTimeout(async () => {
        setSources((p) =>
          p.map((s) =>
            s.id === newSrc.id
              ? {
                  ...s,
                  parsing_status: "completed",
                  authors: `${linkType} • Link • Completed`,
                  file_id: `link_${Date.now()}`
                }
              : s
          )
        );
        setUploadProgress((p) => {
          const clone = { ...p };
          delete clone[uploadId];
          return clone;
        });
        await loadParsedFiles();
      }, 3000);
    };

    // Text upload
    const handleTextUpload = async () => {
      if (!pasteText.trim()) {
        setError("Enter text");
        return;
      }
      setError(null);
      setShowUploadModal(false);
      const uploadId = `text_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const newSrc = {
        id: Date.now(),
        upload_file_id: uploadId,
        title: `Text Content (${pasteText.slice(0, 50)}...)`,
        authors: `TXT • ${(pasteText.length / 1000).toFixed(1)}k chars • Processing...`,
        ext: "txt",
        selected: false,
        type: "uploading",
        parsing_status: "pending",
        metadata: {
          original_filename: "pasted_text.txt",
          file_extension: ".txt",
          content_length: pasteText.length,
          source_type: "text"
        }
      };
      setSources((p) => [...p, newSrc]);
      setUploadProgress((p) => ({ ...p, [uploadId]: 0 }));

      const blob = new Blob([pasteText], { type: "text/plain" });
      const file = new File([blob], "pasted_text.txt", { type: "text/plain" });
      setUploadProgress((p) => ({ ...p, [uploadId]: 20 }));

      try {
        const resp = await apiService.parseFile(file, uploadId, notebookId);
        if (!resp.success) throw new Error(resp.error || "Text upload failed");
        const data = resp.data;
        setSources((p) =>
          p.map((s) =>
            s.id === newSrc.id
              ? {
                  ...s,
                  file_id: data.file_id,
                  type: "parsing",
                  parsing_status: data.status,
                  authors: `TXT • ${(pasteText.length / 1000).toFixed(1)}k chars • ${
                    statusConfig[data.status]?.label || data.status
                  }`,
                  metadata: {
                    ...s.metadata,
                    file_size: data.file_size,
                    file_extension: data.file_extension
                  }
                }
              : s
          )
        );
        startStatusMonitoring(uploadId, newSrc.id);
        setTimeout(loadParsedFiles, 500);
      } catch (err) {
        console.error(err);
        setSources((p) =>
          p.map((s) =>
            s.id === newSrc.id
              ? {
                  ...s,
                  parsing_status: "error",
                  authors: "TXT • Upload failed",
                  error_message: err.message
                }
              : s
          )
        );
        setUploadProgress((p) => {
          const clone = { ...p };
          delete clone[uploadId];
          return clone;
        });
        setError(`Failed to upload text: ${err.message}`);
      }
    };

    const getStatusIcon = (status, animated = false) => {
      const cfg = statusConfig[status] || statusConfig.error;
      const Icon = cfg.icon;
      return (
        <Icon
          className={`h-3 w-3 ${cfg.color} ${
            animated && cfg.animate ? "animate-spin" : ""
          }`}
        />
      );
    };

    const renderFileProgress = (src) => {
      const prog = uploadProgress[src.upload_file_id];
      if (prog != null && ["pending", "parsing"].includes(src.parsing_status)) {
        return (
          <div className="mt-1">
            <Progress value={prog} className="h-1" />
            <div className="text-xs text-gray-400 mt-1">{prog}% complete</div>
          </div>
        );
      }
      return null;
    };

    if (isHidden) {
      return (
        <div className="h-full flex items-center justify-center p-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsHidden(false)}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Expand Sources
          </Button>
        </div>
      );
    }

    return (
      <div className="h-full flex flex-col relative">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-semibold text-red-600">
              Knowledge Base
            </h2>
            {isLoading && (
              <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />
            )}
            <Badge variant="secondary" className="text-xs">
              {sources.length} files
            </Badge>
          </div>
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={loadParsedFiles}
              disabled={isLoading}
              title="Refresh list"
            >
              <ArrowUpDown className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleDeleteSelected}
              disabled={selectedCount === 0}
              title="Delete Selected"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="p-4 border-b border-gray-200"
            >
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  {error}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-2 h-6 px-2"
                    onClick={() => setError(null)}
                  >
                    Dismiss
                  </Button>
                </AlertDescription>
              </Alert>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Select All */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="selectAll"
                className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500"
                checked={
                  sources.length > 0 && selectedCount === sources.length
                }
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSources((prev) =>
                    prev.map((s) => ({ ...s, selected: checked }))
                  );
                  if (onSelectionChange) setTimeout(onSelectionChange, 0);
                }}
              />
              <label
                htmlFor="selectAll"
                className="ml-2 text-sm text-gray-700"
              >
                Select All ({selectedCount} selected)
              </label>
            </div>
            {selectedCount > 0 && (
              <Badge variant="outline" className="text-xs">
                {selectedCount} selected
              </Badge>
            )}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence>
            {sources.map((src) => (
              <motion.div
                key={src.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.2 }}
                className={`p-4 border-b border-gray-200 flex ${
                  src.selected ? "bg-red-50" : ""
                } ${
                  src.parsing_status === "error"
                    ? "border-l-4 border-l-red-300"
                    : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={src.selected}
                  disabled={["pending", "parsing"].includes(
                    src.parsing_status
                  )}
                  onChange={() => toggleSource(src.id)}
                  className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500 mt-1"
                />
                <div className="ml-3 flex items-start space-x-2 flex-1 min-w-0">
                  <span className="text-lg flex-shrink-0">
                    {fileIcons[src.ext] || "📁"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {src.title}
                      </h3>
                      {src.parsing_status &&
                        getStatusIcon(
                          src.parsing_status,
                          ["pending", "parsing"].includes(src.parsing_status)
                        )}
                    </div>
                    <p className="text-xs text-gray-500 mb-1">
                      {src.authors}
                    </p>
                    {renderFileProgress(src)}
                    {src.error_message && (
                      <p
                        className="text-xs text-red-600 mt-1 truncate"
                        title={src.error_message}
                      >
                        Error: {src.error_message}
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {!isLoading && sources.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <Upload className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p className="text-sm">No files in knowledge base</p>
              <p className="text-xs text-gray-400 mt-1">
                Upload your first file to get started
              </p>
            </div>
          )}

          {isLoading && sources.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              <RefreshCw className="h-12 w-12 mx-auto mb-4 text-gray-300 animate-spin" />
              <p className="text-sm">Loading files...</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-gray-500">
              {sources.length} total • {selectedCount} selected
            </p>
            {Object.keys(uploadProgress).length > 0 && (
              <p className="text-xs text-blue-600">
                {Object.keys(uploadProgress).length} processing…
              </p>
            )}
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full flex items-center justify-center"
            onClick={handleAddSource}
            disabled={isLoading}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Source
          </Button>

          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChangeInternal}
            accept=".pdf,.txt,.md,.ppt,.pptx,.mp3,.mp4"
          />

          <p className="text-xs text-gray-400 mt-2 text-center">
            Supports PDF, TXT, MD, PPT, MP3, MP4 (max 100MB)
          </p>
        </div>

        {/* Upload Modal */}
        <AnimatePresence>
          {showUploadModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-[60] p-4"
              onClick={() => setShowUploadModal(false)}
            >
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                transition={{ type: "spring", duration: 0.5 }}
                className="bg-gray-900 rounded-2xl p-8 max-w-3xl w-full max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-2xl font-bold text-white">
                    Upload sources
                  </h2>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowUploadModal(false)}
                    className="text-gray-400 hover:text-white hover:bg-gray-800"
                  >
                    <X className="h-6 w-6" />
                  </Button>
                </div>

                {/* Drag & Drop */}
                <div
                  className={`border-2 border-dashed rounded-xl p-12 mb-8 text-center transition-all duration-200 ${
                    isDragOver
                      ? "border-blue-400 bg-blue-900/20"
                      : "border-gray-600 bg-gray-800/50"
                  }`}
                  onDragEnter={handleDragEnter}
                  onDragLeave={handleDragLeave}
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                >
                  <div className="flex flex-col items-center space-y-4">
                    <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
                      <Upload className="h-8 w-8 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-white mb-2">
                        Upload sources
                      </h3>
                      <p className="text-gray-400">
                        Drag & drop or{" "}
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          className="text-blue-400 hover:text-blue-300 underline"
                        >
                          choose file to upload
                        </button>
                      </p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-500 mt-6">
                    Supported file types: PDF, .txt, Markdown, Audio (e.g. mp3)
                  </p>
                </div>

                {/* Link & Text Sections */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Link */}
                  <div className="bg-gray-800 rounded-xl p-6">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                        <Link2 className="h-5 w-5 text-white" />
                      </div>
                      <h3 className="text-lg font-semibold text-white">Link</h3>
                    </div>
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          className="flex items-center space-x-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                          onClick={() => setActiveTab("link")}
                        >
                          <Globe className="h-4 w-4 text-gray-300" />
                          <span className="text-sm text-gray-300">Website</span>
                        </button>
                        <button
                          className="flex items-center space-x-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                          onClick={() => setActiveTab("link")}
                        >
                          <Youtube className="h-4 w-4 text-red-400" />
                          <span className="text-sm text-gray-300">
                            YouTube
                          </span>
                        </button>
                      </div>
                      {activeTab === "link" && (
                        <div className="space-y-3">
                          <input
                            type="url"
                            placeholder="Enter URL (website or YouTube)"
                            value={linkUrl}
                            onChange={(e) => setLinkUrl(e.target.value)}
                            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                          <Button
                            onClick={handleLinkUpload}
                            disabled={!linkUrl.trim()}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                          >
                            Process Link
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Text */}
                  <div className="bg-gray-800 rounded-xl p-6">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                        <FileText className="h-5 w-5 text-white" />
                      </div>
                      <h3 className="text-lg font-semibold text-white">
                        Paste text
                      </h3>
                    </div>
                    <div className="space-y-3">
                      <button
                        className="flex items-center space-x-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors w-full"
                        onClick={() => setActiveTab("text")}
                      >
                        <FileText className="h-4 w-4 text-gray-300" />
                        <span className="text-sm text-gray-300">
                          Copied text
                        </span>
                      </button>
                      {activeTab === "text" && (
                        <div className="space-y-3">
                          <textarea
                            placeholder="Paste your text content here..."
                            value={pasteText}
                            onChange={(e) => setPasteText(e.target.value)}
                            rows={6}
                            className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                          />
                          <div className="flex items-center justify-between text-xs text-gray-400">
                            <span>{pasteText.length} characters</span>
                            <span>1 / 50</span>
                          </div>
                          <Button
                            onClick={handleTextUpload}
                            disabled={!pasteText.trim()}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                          >
                            Upload Text
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }
);

export default SourcesList;
