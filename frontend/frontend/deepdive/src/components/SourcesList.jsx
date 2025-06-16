// import React, { useState } from "react";
// import { ArrowUpDown, Trash2, Plus } from "lucide-react";
// import { motion } from "framer-motion";
// import { Button } from "@/components/ui/button";
// import SourceModal from "@/components/ui/SourceModal";

// const fileIcons = {
//   pdf: "📄", txt: "📃", md: "📝", ppt: "📊", mp3: "🎵", mp4: "🎞️", url: "🔗"
// };

// const SourcesList = () => {
//   const [sources, setSources] = useState([]);
//   const [modalOpen, setModalOpen] = useState(false);

//   const toggleSource = (id) => {
//     setSources((prev) =>
//       prev.map((s) => (s.id === id ? { ...s, selected: !s.selected } : s))
//     );
//   };

//   const handleAddSources = async (incoming) => {
//     const updated = await Promise.all(
//       incoming.map(async (s) => {
//         if (s.ext === "url" && s.link) {
//           try {
//             const controller = new AbortController();
//             const timeout = setTimeout(() => controller.abort(), 3000); // timeout fetch

//             const res = await fetch(
//               `https://jsonlink.io/api/extract?url=${encodeURIComponent(s.link)}`,
//               { signal: controller.signal }
//             );

//             clearTimeout(timeout);

//             if (!res.ok) throw new Error("Bad response");
//             const meta = await res.json();

//             return {
//               ...s,
//               title: meta.title || s.title,
//               authors: meta.description || "Website",
//             };
//           } catch (err) {
//             return {
//               ...s,
//               authors: "Unavailable",
//               title: s.link,
//             };
//           }
//         }
//         return s;
//       })
//     );

//     setSources((prev) => [...prev, ...updated]);
//   };


//   const handleDeleteSelected = () => {
//     setSources((prev) => prev.filter((s) => !s.selected));
//   };

//   const selectedCount = sources.filter((s) => s.selected).length;

//   return (
//     <div className="h-full flex flex-col relative">
//       <div className="p-4 border-b border-gray-200 flex justify-between items-center">
//         <h2 className="text-lg font-semibold text-red-600">Sources</h2>
//         <div className="flex items-center space-x-1">
//           <Button variant="ghost" size="icon" className="h-8 w-8">
//             <ArrowUpDown className="h-4 w-4" />
//           </Button>
//           <Button
//             variant="ghost"
//             size="icon"
//             className="h-8 w-8"
//             onClick={handleDeleteSelected}
//           >
//             <Trash2 className="h-4 w-4" />
//           </Button>
//         </div>
//       </div>

//       <div className="p-4 border-b border-gray-200">
//         <label className="flex items-center text-sm text-gray-700">
//           <input
//             type="checkbox"
//             className="h-4 w-4 rounded border-gray-300 text-red-600"
//             onChange={(e) => {
//               const checked = e.target.checked;
//               setSources((prev) => prev.map((s) => ({ ...s, selected: checked })));
//             }}
//           />
//           <span className="ml-2">Select All</span>
//         </label>
//       </div>

//       <div className="flex-1 overflow-y-auto">
//         {sources.map((s) => (
//           <motion.div
//             key={s.id}
//             initial={{ opacity: 0 }}
//             animate={{ opacity: 1 }}
//             transition={{ duration: 0.3 }}
//             className={`p-4 border-b border-gray-200 flex ${s.selected ? "bg-red-50" : ""}`}
//           >
//             <input
//               type="checkbox"
//               checked={s.selected}
//               onChange={() => toggleSource(s.id)}
//               className="h-4 w-4 mt-1 text-red-600"
//             />
//             <div className="ml-3 space-y-1">
//               <div className="flex items-center space-x-2">
//                 <span className="text-lg">{fileIcons[s.ext] || "📁"}</span>
//                 <h3 className="text-sm font-medium text-gray-900">{s.title}</h3>
//               </div>
//               <p className="text-xs text-gray-500">{s.authors}</p>
//               {s.link && (
//                 <a
//                   href={s.link}
//                   target="_blank"
//                   rel="noreferrer"
//                   className="text-xs text-blue-600 underline"
//                 >
//                   {s.link}
//                 </a>
//               )}
//             </div>
//           </motion.div>
//         ))}
//       </div>

//       <div className="p-4 border-t border-gray-200">
//         <p className="text-xs text-gray-500 mb-4">
//           {selectedCount} source{selectedCount !== 1 ? "s" : ""} selected
//         </p>
//         <Button
//           variant="outline"
//           size="sm"
//           className="w-full"
//           onClick={() => setModalOpen(true)}
//         >
//           <Plus className="h-4 w-4 mr-2" />
//           Add More Source
//         </Button>
//       </div>

//       {modalOpen && (
//         <SourceModal
//           onClose={() => setModalOpen(false)}
//           onAddSources={handleAddSources}
//         />
//       )}

//     </div>
//   );
// };

// export default SourcesList;

import React, { useState, useRef, useImperativeHandle, forwardRef, useEffect, useCallback } from "react";
import { ArrowUpDown, Trash2, Plus, ChevronLeft, RefreshCw, CheckCircle, AlertCircle, Clock, X, Upload, Link2, FileText, Globe, Youtube } from "lucide-react";
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
  pending: { icon: Clock, color: "text-yellow-500", bg: "bg-yellow-50", label: "Queued" },
  parsing: { icon: RefreshCw, color: "text-blue-500", bg: "bg-blue-50", label: "Processing", animate: true },
  completed: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-50", label: "Completed" },
  error: { icon: AlertCircle, color: "text-red-500", bg: "bg-red-50", label: "Failed" },
  cancelled: { icon: X, color: "text-gray-500", bg: "bg-gray-50", label: "Cancelled" },
  unsupported: { icon: AlertCircle, color: "text-orange-500", bg: "bg-orange-50", label: "Unsupported" }
};

const SourcesList = forwardRef(({ onSelectionChange, ...props }, ref) => {
  const [sources, setSources] = useState([]);
  const [isHidden, setIsHidden] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const fileInputRef = useRef(null);
  
  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [pasteText, setPasteText] = useState('');
  const [activeTab, setActiveTab] = useState('file'); // 'file', 'link', 'text'

  // SSE connections for status updates
  const sseConnectionsRef = useRef(new Map());

  // Load parsed files on component mount
  useEffect(() => {
    loadParsedFiles();
    
    // Cleanup SSE connections on unmount
    return () => {
      sseConnectionsRef.current.forEach((eventSource) => {
        eventSource.close();
      });
      sseConnectionsRef.current.clear();
    };
  }, []);

  const loadParsedFiles = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await apiService.listParsedFiles();
      
      if (response.success) {
        const parsedSources = response.data.map(metadata => ({
          id: metadata.file_id,
          title: metadata.original_filename,
          authors: generateFileDescription(metadata),
          ext: metadata.file_extension?.substring(1) || "unknown", // Remove the dot
          selected: false,
          type: "parsed",
          file_id: metadata.file_id,
          upload_file_id: metadata.upload_file_id,
          parsing_status: metadata.parsing_status,
          metadata: metadata,
          error_message: metadata.error_message
        }));
        
        setSources(parsedSources);
      } else {
        throw new Error(response.error || "Failed to load files");
      }
    } catch (error) {
      console.error('Error loading parsed files:', error);
      setError(`Failed to load files: ${error.message}`);
      setSources([]);
    } finally {
      setIsLoading(false);
    }
  };

  const generateFileDescription = (metadata) => {
    const size = metadata.file_size ? `${(metadata.file_size / (1024 * 1024)).toFixed(1)} MB` : 
                 metadata.content_length ? `${(metadata.content_length / 1000).toFixed(1)}k chars` : 'Unknown size';
    const status = statusConfig[metadata.parsing_status]?.label || metadata.parsing_status;
    const ext = metadata.file_extension?.toUpperCase().replace('.', '') || 'Unknown';
    
    return `${ext} • ${size} • ${status}`;
  };

  // Start SSE monitoring for file status
  const startStatusMonitoring = useCallback((uploadFileId, sourceId) => {
    // Don't start multiple connections for the same file
    if (sseConnectionsRef.current.has(uploadFileId)) {
      return;
    }

    const onMessage = (data) => {
      console.log('SSE status update received:', data);
      
      if (data.error) {
        console.error('SSE status error:', data.error);
        return;
      }

      const { status, job_details } = data;
      
      // Update progress if available
      if (job_details?.progress_percentage !== undefined) {
        setUploadProgress(prev => ({
          ...prev,
          [uploadFileId]: job_details.progress_percentage
        }));
      }
      
      // Update source status
      setSources(prev => prev.map(source => 
        source.id === sourceId ? {
          ...source,
          parsing_status: status,
          authors: job_details ? 
            generateFileDescription({
              ...source.metadata,
              parsing_status: status,
              content_length: job_details.result?.content_length || source.metadata?.content_length
            }) : 
            source.authors,
          metadata: job_details?.result?.metadata || source.metadata,
          error_message: job_details?.error
        } : source
      ));
      
      // Close SSE connection if parsing is complete
      if (['completed', 'error', 'cancelled', 'unsupported'].includes(status)) {
        const eventSource = sseConnectionsRef.current.get(uploadFileId);
        if (eventSource) {
          eventSource.close();
          sseConnectionsRef.current.delete(uploadFileId);
        }
        
        // Clear upload progress
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[uploadFileId];
          return newProgress;
        });
        
        // If completed successfully, reload the file list to get updated data
        if (status === 'completed') {
          setTimeout(loadParsedFiles, 1000);
        }
      }
    };

    const onError = (error) => {
      console.error('SSE connection error for', uploadFileId, ':', error);
      
      // Close and remove the connection
      const eventSource = sseConnectionsRef.current.get(uploadFileId);
      if (eventSource) {
        eventSource.close();
        sseConnectionsRef.current.delete(uploadFileId);
      }
      
      // Update source to show error after connection failure
      setSources(prev => prev.map(source => 
        source.id === sourceId ? {
          ...source,
          parsing_status: "error",
          authors: source.authors.replace(/Processing|Queued/, "Connection Failed"),
          error_message: "Lost connection to server during processing"
        } : source
      ));
      
      // Clear progress
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[uploadFileId];
        return newProgress;
      });
    };

    const onClose = () => {
      console.log('SSE connection closed for', uploadFileId);
      sseConnectionsRef.current.delete(uploadFileId);
    };

    try {
      // Create SSE connection
      const eventSource = apiService.createParsingStatusStream(uploadFileId, onMessage, onError, onClose);
      sseConnectionsRef.current.set(uploadFileId, eventSource);
      console.log('SSE connection established for', uploadFileId);
    } catch (error) {
      console.error('Failed to create SSE connection for', uploadFileId, ':', error);
      onError(error);
    }
  }, []);

  // Expose methods to parent components
  useImperativeHandle(ref, () => ({
    getSelectedFiles: () => {
      return sources.filter(source => 
        source.selected && 
        (source.file_id || source.file) && 
        source.parsing_status === 'completed'
      );
    },
    getSelectedSources: () => {
      return sources.filter(source => source.selected);
    },
    clearSelection: () => {
      setSources(prev => prev.map(source => ({ ...source, selected: false })));
    },
    refreshSources: loadParsedFiles
  }));

  const toggleSource = (id) => {
    setSources((prev) => {
      const newSources = prev.map((source) =>
        source.id === id ? { ...source, selected: !source.selected } : source
      );
      
      // Notify parent component about selection change
      if (onSelectionChange) {
        // Use setTimeout to ensure state update is complete
        setTimeout(() => onSelectionChange(), 0);
      }
      
      return newSources;
    });
  };

  const handleDeleteSelected = async () => {
    const selectedSources = sources.filter(source => source.selected);
    
    if (selectedSources.length === 0) {
      return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedSources.length} selected source(s)?`)) {
      return;
    }
    
    console.log('Deleting selected sources:', selectedSources);
    
    // Track which deletions succeed
    const deletionResults = [];
    
    // Delete files from backend
    for (const source of selectedSources) {
      try {
        console.log('Attempting to delete source:', source);
        
        let result;
        if (source.upload_file_id) {
          console.log('Using deleteFileByUploadId for:', source.upload_file_id);
          result = await apiService.deleteFileByUploadId(source.upload_file_id);
          
          // Stop any SSE connection for this file
          const eventSource = sseConnectionsRef.current.get(source.upload_file_id);
          if (eventSource) {
            eventSource.close();
            sseConnectionsRef.current.delete(source.upload_file_id);
          }
        } else if (source.file_id) {
          console.log('Using deleteParsedFile for:', source.file_id);
          result = await apiService.deleteParsedFile(source.file_id);
        } else {
          console.warn('Source has neither upload_file_id nor file_id:', source);
          continue;
        }
        
        console.log('Delete result:', result);
        
        if (result.success) {
          deletionResults.push({ source, success: true });
        } else {
          deletionResults.push({ source, success: false, error: result.error });
        }
      } catch (error) {
        console.error(`Error deleting file ${source.title}:`, error);
        deletionResults.push({ source, success: false, error: error.message });
      }
    }
    
    // Remove successfully deleted sources from frontend state
    const successfullyDeleted = deletionResults
      .filter(result => result.success)
      .map(result => result.source.id);
    
    setSources((prev) => prev.filter((source) => !successfullyDeleted.includes(source.id)));
    
    // Show error for failed deletions
    const failedDeletions = deletionResults.filter(result => !result.success);
    if (failedDeletions.length > 0) {
      const errorMessage = `Failed to delete ${failedDeletions.length} file(s): ${failedDeletions.map(f => f.source.title).join(', ')}`;
      setError(errorMessage);
    }
  };

  const selectedCount = sources.filter((s) => s.selected).length;

  const handleAddSource = () => {
    setShowUploadModal(true);
    setActiveTab('file');
    setLinkUrl('');
    setPasteText('');
  };

  // Modified file upload handler
  const handleFileUpload = async (file) => {
    // Validate file
    const validation = validateFile(file);
    
    if (!validation.valid) {
      setError(`File validation failed: ${validation.errors.join(', ')}`);
      return;
    }
    
    // Close modal and process file
    setShowUploadModal(false);
    
    // Use existing handleFileChange logic but with the file parameter
    const event = { target: { files: [file], value: "" } };
    await handleFileChangeInternal(event);
  };

  // Drag and drop handlers
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, []);

  // Handle link upload
  const handleLinkUpload = async () => {
    if (!linkUrl.trim()) {
      setError('Please enter a valid URL');
      return;
    }

    try {
      setError(null);
      setShowUploadModal(false);
      
      // Generate upload file ID for tracking
      const uploadFileId = `link_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Determine the type of link
      const isYoutube = linkUrl.includes('youtube.com') || linkUrl.includes('youtu.be');
      const linkType = isYoutube ? 'YouTube' : 'Website';
      
      // Add link to sources with initial status
      const newSource = {
        id: Date.now(),
        upload_file_id: uploadFileId,
        title: linkUrl,
        authors: `${linkType} • Link • Processing...`,
        ext: 'link',
        selected: false,
        type: "uploading",
        parsing_status: "pending",
        metadata: {
          original_filename: linkUrl,
          file_extension: '.url',
          source_type: 'link'
        }
      };
      
      setSources((prev) => [...prev, newSource]);
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 0 }));

      // Call API to process the link
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 20 }));
      
      // TODO: Add actual API call for link processing
      // For now, simulate processing
      setTimeout(() => {
        setSources((prev) => prev.map(source => 
          source.id === newSource.id ? {
            ...source,
            parsing_status: "completed",
            authors: `${linkType} • Link • Completed`,
            file_id: `link_${Date.now()}`
          } : source
        ));
        
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[uploadFileId];
          return newProgress;
        });
      }, 3000);
      
    } catch (error) {
      console.error('Error processing link:', error);
      setError(`Failed to process link: ${error.message}`);
    }
  };

  // Handle text upload
  const handleTextUpload = async () => {
    if (!pasteText.trim()) {
      setError('Please enter some text content');
      return;
    }

    try {
      setError(null);
      setShowUploadModal(false);
      
      // Generate upload file ID for tracking
      const uploadFileId = `text_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Add text to sources with initial status
      const newSource = {
        id: Date.now(),
        upload_file_id: uploadFileId,
        title: `Text Content (${pasteText.slice(0, 50)}...)`,
        authors: `TXT • ${(pasteText.length / 1000).toFixed(1)}k chars • Processing...`,
        ext: 'txt',
        selected: false,
        type: "uploading",
        parsing_status: "pending",
        metadata: {
          original_filename: 'pasted_text.txt',
          file_extension: '.txt',
          content_length: pasteText.length,
          source_type: 'text'
        }
      };
      
      setSources((prev) => [...prev, newSource]);
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 0 }));

      // Create a virtual file from the text
      const blob = new Blob([pasteText], { type: 'text/plain' });
      const file = new File([blob], 'pasted_text.txt', { type: 'text/plain' });
      
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 20 }));
      
      // Use existing file upload logic
      const response = await apiService.parseFile(file, uploadFileId);
      
      if (response.success) {
        const { data } = response;
        
        setSources((prev) => prev.map(source => 
          source.id === newSource.id ? {
            ...source,
            file_id: data.file_id,
            type: "parsing",
            parsing_status: data.status,
            authors: `TXT • ${(pasteText.length / 1000).toFixed(1)}k chars • ${statusConfig[data.status]?.label || data.status}`,
            metadata: {
              ...source.metadata,
              file_size: data.file_size,
              file_extension: data.file_extension
            }
          } : source
        ));
        
        startStatusMonitoring(uploadFileId, newSource.id);
        
      } else {
        throw new Error(response.error || 'Text upload failed');
      }
      
    } catch (error) {
      console.error('Error processing text:', error);
      
      setSources((prev) => prev.map(source => 
        source.id === newSource.id ? {
          ...source,
          parsing_status: "error",
          authors: `TXT • Upload failed`,
          error_message: error.message
        } : source
      ));
      
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[uploadFileId];
        return newProgress;
      });
      
      setError(`Failed to upload text: ${error.message}`);
    }
  };

  const validateFile = (file) => {
    const allowedExtensions = ["pdf", "txt", "md", "ppt", "pptx", "mp3", "mp4"];
    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    const maxSize = 100 * 1024 * 1024; // 100MB
    const minSize = 100; // 100 bytes minimum
    
    const errors = [];
    const warnings = [];
    
    // Check file extension
    if (!extension) {
      errors.push("File must have an extension");
    } else if (!allowedExtensions.includes(extension)) {
      errors.push(`File type "${extension}" is not supported. Allowed types: ${allowedExtensions.join(', ')}`);
    }
    
    // Check file size
    if (file.size > maxSize) {
      errors.push(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum allowed size of 100MB`);
    } else if (file.size < minSize) {
      warnings.push("File is very small and may be empty");
    }
    
    // Check filename for potentially dangerous characters
    if (/[<>:"|?*]/.test(file.name)) {
      errors.push("Filename contains invalid characters");
    }
    
    // Check MIME type if available
    if (file.type) {
      const expectedTypes = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4"
      };
      
      const expectedType = expectedTypes[extension];
      if (expectedType && !file.type.startsWith(expectedType.split('/')[0])) {
        warnings.push(`File type "${file.type}" may not match extension "${extension}"`);
      }
    }
    
    return { valid: errors.length === 0, errors, warnings, extension };
  };

  const handleFileChangeInternal = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file
      const validation = validateFile(file);
      
      if (!validation.valid) {
        setError(`File validation failed: ${validation.errors.join(', ')}`);
        return;
      }
      
      // Show warnings if any
      if (validation.warnings.length > 0) {
        console.warn('File validation warnings:', validation.warnings);
      }

      // Clear previous errors
      setError(null);

      // Generate upload file ID for tracking
      const uploadFileId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Add file to sources with initial status
      const newSource = {
        id: Date.now(),
        upload_file_id: uploadFileId,
        title: file.name,
        authors: `${validation.extension.toUpperCase()} • ${(file.size / (1024 * 1024)).toFixed(1)} MB • Uploading...`,
        ext: validation.extension,
        selected: false,
        type: "uploading",
        file: file,
        parsing_status: "pending",
        metadata: {
          original_filename: file.name,
          file_extension: `.${validation.extension}`,
          file_size: file.size
        }
      };
      
      setSources((prev) => [...prev, newSource]);
      
      // Initialize upload progress
      setUploadProgress(prev => ({ ...prev, [uploadFileId]: 0 }));

      try {
        // Upload and parse file
        setUploadProgress(prev => ({ ...prev, [uploadFileId]: 10 }));
        
        const response = await apiService.parseFile(file, uploadFileId);
        
        if (response.success) {
          const { data } = response;
          
          // Update the source with response information
          setSources((prev) => prev.map(source => 
            source.id === newSource.id ? {
              ...source,
              file_id: data.file_id,
              type: "parsing",
              parsing_status: data.status,
              authors: `${validation.extension.toUpperCase()} • ${(data.file_size / (1024 * 1024)).toFixed(1)} MB • ${statusConfig[data.status]?.label || data.status}`,
              metadata: {
                ...source.metadata,
                file_size: data.file_size,
                file_extension: data.file_extension
              }
            } : source
          ));
          
          // Start status polling for real-time updates
          startStatusMonitoring(uploadFileId, newSource.id);
          
        } else {
          // Handle upload failure
          throw new Error(response.error || 'Upload failed');
        }
      } catch (error) {
        console.error('Error uploading file:', error);
        
        // Update source to show error
        setSources((prev) => prev.map(source => 
          source.id === newSource.id ? {
            ...source,
            parsing_status: "error",
            authors: `${validation.extension.toUpperCase()} • Upload failed`,
            error_message: error.message
          } : source
        ));
        
        // Clear progress
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[uploadFileId];
          return newProgress;
        });
        
        setError(`Failed to upload ${file.name}: ${error.message}`);
      }

      // Reset file input
      event.target.value = "";
    }
  };

  // Handle file change from modal file input
  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (file) {
      await handleFileUpload(file);
    }
  };

  const getStatusIcon = (status, isAnimated = false) => {
    const config = statusConfig[status] || statusConfig.error;
    const IconComponent = config.icon;
    
    return (
      <IconComponent 
        className={`h-3 w-3 ${config.color} ${isAnimated && config.animate ? 'animate-spin' : ''}`} 
      />
    );
  };

  const renderFileProgress = (source) => {
    const progress = uploadProgress[source.upload_file_id];
    
    if (progress !== undefined && ['pending', 'parsing'].includes(source.parsing_status)) {
      return (
        <div className="mt-1">
          <Progress value={progress} className="h-1" />
          <div className="text-xs text-gray-400 mt-1">{progress}% complete</div>
        </div>
      );
    }
    
    return null;
  };

  if (isHidden) {
    return (
      <div className="h-full flex items-center justify-center p-4">
        <Button variant="outline" size="sm" onClick={() => setIsHidden(false)}>
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
          <h2 className="text-lg font-semibold text-red-600">Knowledge Base</h2>
          {isLoading && <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />}
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

      {/* Error Display */}
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
              checked={sources.length > 0 && selectedCount === sources.length}
              onChange={(e) => {
                const checked = e.target.checked;
                setSources((prev) => {
                  const newSources = prev.map((s) => ({ ...s, selected: checked }));
                  
                  // Notify parent component about selection change
                  if (onSelectionChange) {
                    setTimeout(() => onSelectionChange(), 0);
                  }
                  
                  return newSources;
                });
              }}
            />
            <label htmlFor="selectAll" className="ml-2 text-sm text-gray-700">
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

      {/* Source List */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence>
          {sources.map((source) => (
            <motion.div
              key={source.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              className={`p-4 border-b border-gray-200 flex ${
                source.selected ? "bg-red-50" : ""
              } ${source.parsing_status === 'error' ? 'border-l-4 border-l-red-300' : ''}`}
            >
              <input
                type="checkbox"
                checked={source.selected}
                onChange={() => toggleSource(source.id)}
                className="h-4 w-4 rounded border-gray-300 text-red-600 focus:ring-red-500 mt-1"
                disabled={['pending', 'parsing'].includes(source.parsing_status)}
              />
              <div className="ml-3 flex items-start space-x-2 flex-1 min-w-0">
                <span className="text-lg flex-shrink-0">
                  {fileIcons[source.ext] || "📁"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {source.title}
                    </h3>
                    {source.parsing_status && getStatusIcon(
                      source.parsing_status, 
                      ['pending', 'parsing'].includes(source.parsing_status)
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mb-1">{source.authors}</p>
                  
                  {/* Progress bar for ongoing uploads/parsing */}
                  {renderFileProgress(source)}
                  
                  {/* Error message display */}
                  {source.error_message && (
                    <p className="text-xs text-red-600 mt-1 truncate" title={source.error_message}>
                      Error: {source.error_message}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {/* Empty state */}
        {!isLoading && sources.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            <Upload className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-sm">No files in knowledge base</p>
            <p className="text-xs text-gray-400 mt-1">Upload your first file to get started</p>
          </div>
        )}
        
        {/* Loading state */}
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
              {Object.keys(uploadProgress).length} processing...
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
          onChange={handleFileChange}
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
                <h2 className="text-2xl font-bold text-white">Upload sources</h2>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-400 hover:text-white hover:bg-gray-800"
                >
                  <X className="h-6 w-6" />
                </Button>
              </div>

              {/* Main Upload Area */}
              <div
                className={`border-2 border-dashed rounded-xl p-12 mb-8 text-center transition-all duration-200 ${
                  isDragOver 
                    ? 'border-blue-400 bg-blue-900/20' 
                    : 'border-gray-600 bg-gray-800/50'
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
                    <h3 className="text-xl font-semibold text-white mb-2">Upload sources</h3>
                    <p className="text-gray-400">
                      Drag & drop or{' '}
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

              {/* Upload Options */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Link Section */}
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
                        onClick={() => setActiveTab('link')}
                      >
                        <Globe className="h-4 w-4 text-gray-300" />
                        <span className="text-sm text-gray-300">Website</span>
                      </button>
                      <button 
                        className="flex items-center space-x-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                        onClick={() => setActiveTab('link')}
                      >
                        <Youtube className="h-4 w-4 text-red-400" />
                        <span className="text-sm text-gray-300">YouTube</span>
                      </button>
                    </div>
                    
                    {activeTab === 'link' && (
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

                {/* Paste Text Section */}
                <div className="bg-gray-800 rounded-xl p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                      <FileText className="h-5 w-5 text-white" />
                    </div>
                    <h3 className="text-lg font-semibold text-white">Paste text</h3>
                  </div>
                  
                  <div className="space-y-3">
                    <button 
                      className="flex items-center space-x-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors w-full"
                      onClick={() => setActiveTab('text')}
                    >
                      <FileText className="h-4 w-4 text-gray-300" />
                      <span className="text-sm text-gray-300">Copied text</span>
                    </button>
                    
                    {activeTab === 'text' && (
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
});

export default SourcesList;