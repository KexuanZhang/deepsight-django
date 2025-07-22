import { 
  File, FileText, Globe, Music, Video, Presentation, 
  Clock, RefreshCw, CheckCircle, AlertCircle, X 
} from "lucide-react";

/**
 * Configuration objects for file management
 * Centralizes file type mappings, status configurations, and validation rules
 */

// File type icon mappings
export const FILE_ICONS = {
  pdf: File,
  txt: FileText,
  md: FileText, 
  pptx: Presentation,
  docx: FileText,
  mp3: Music,
  mp4: Video,
  wav: Music,
  m4a: Music,
  avi: Video,
  mov: Video,
  mkv: Video,
  webm: Video,
  flv: Video,
  wmv: Video,
  '3gp': Video,
  ogv: Video,
  'm4v': Video,
  url: Globe,
  website: Globe,
  media: Video
};

// File status configurations
export const STATUS_CONFIG = {
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

// File validation configuration
export const VALIDATION_CONFIG = {
  allowedExtensions: [
    "pdf", "txt", "md", "pptx", "docx", 
    "mp3", "mp4", "wav", "m4a", "avi", "mov", "mkv", 
    "webm", "flv", "wmv", "3gp", "ogv", "m4v"
  ],
  maxSize: 100 * 1024 * 1024, // 100MB
  minSize: 100, // 100 bytes
  expectedMimeTypes: {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "flv": "video/x-flv",
    "wmv": "video/x-ms-wmv",
    "3gp": "video/3gpp",
    "ogv": "video/ogg",
    "m4v": "video/x-m4v"
  },
  acceptString: ".pdf,.txt,.md,.pptx,.docx,.mp3,.mp4,.wav,.m4a,.avi,.mov,.mkv,.webm,.flv,.wmv,.3gp,.ogv,.m4v"
};

// Video format compatibility information
export const VIDEO_COMPATIBILITY = {
  'mkv': {
    supported: false,
    reason: 'MKV files have limited browser support',
    suggestion: 'Try downloading the file and playing in VLC or another media player'
  },
  'flv': {
    supported: false,
    reason: 'FLV format is no longer supported by modern browsers',
    suggestion: 'Consider converting to MP4 format for web playback'
  },
  'wmv': {
    supported: false,
    reason: 'WMV files are not supported in most browsers',
    suggestion: 'Try downloading the file and playing in a Windows media player'
  },
  'avi': {
    supported: 'partial',
    reason: 'AVI support depends on the internal codecs used',
    suggestion: 'If playback fails, download and use a dedicated media player'
  },
  'webm': {
    supported: true,
    reason: 'WebM is well-supported in modern browsers'
  },
  'mp4': {
    supported: true,
    reason: 'MP4 is universally supported'
  },
  'mov': {
    supported: 'partial',
    reason: 'MOV support varies by browser and codec',
    suggestion: 'If playback fails, try Safari or download the file'
  }
};

// Audio MIME type mappings
export const AUDIO_MIME_TYPES = {
  'mp3': 'audio/mpeg',
  'wav': 'audio/wav',
  'm4a': 'audio/mp4',
  'aac': 'audio/aac',
  'ogg': 'audio/ogg',
  'flac': 'audio/flac'
};

// Video MIME type mappings
export const VIDEO_MIME_TYPES = {
  'mp4': 'video/mp4',
  'webm': 'video/webm',
  'ogg': 'video/ogg',
  'avi': 'video/x-msvideo',
  'mov': 'video/quicktime',
  'wmv': 'video/x-ms-wmv',
  'flv': 'video/x-flv',
  'mkv': 'video/x-matroska',
  '3gp': 'video/3gpp',
  'ogv': 'video/ogg',
  'm4v': 'video/x-m4v'
};

// Chat suggestion configurations
export const CHAT_SUGGESTIONS = [
  { text: "Give me an overview of all my documents", icon: FileText },
  { text: "What are the most important insights and findings?", icon: AlertCircle },
  { text: "How do these sources relate to each other?", icon: RefreshCw },
  { text: "Help me explore a specific topic in depth", icon: Globe }
];

// Layout configurations
export const LAYOUT_RATIOS = {
  sources: 3,    // 3fr for sources panel
  chat: 6.5,     // 6.5fr for chat panel  
  studio: 4.5    // 4.5fr for studio panel
};

// Utility functions for configurations
export const getFileIcon = (extension: string) => {
  return FILE_ICONS[extension?.toLowerCase() as keyof typeof FILE_ICONS] || File;
};

export const getStatusConfig = (status: string) => {
  return STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.error;
};

export const getVideoCompatibility = (format: string) => {
  const formatLower = format?.toLowerCase();
  return VIDEO_COMPATIBILITY[formatLower as keyof typeof VIDEO_COMPATIBILITY] || {
    supported: 'unknown',
    reason: 'Browser support for this format may vary'
  };
};

export const getAudioMimeType = (format: string) => {
  return AUDIO_MIME_TYPES[format?.toLowerCase() as keyof typeof AUDIO_MIME_TYPES] || `audio/${format?.toLowerCase()}`;
};

export const getVideoMimeType = (format: string) => {
  return VIDEO_MIME_TYPES[format?.toLowerCase() as keyof typeof VIDEO_MIME_TYPES] || `video/${format?.toLowerCase()}`;
};