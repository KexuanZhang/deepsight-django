// ====== SINGLE RESPONSIBILITY PRINCIPLE (SRP) ======
// Component focused solely on displaying file content

import React, { useState } from 'react';
import { 
  X, 
  Edit, 
  Save, 
  Download,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

// ====== SINGLE RESPONSIBILITY: Markdown content renderer ======
const MarkdownContent = React.memo(({ content }) => (
  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-blue-600 prose-strong:text-gray-900 prose-code:text-red-600 prose-pre:bg-gray-50">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
    >
      {content}
    </ReactMarkdown>
  </div>
));

MarkdownContent.displayName = 'MarkdownContent';

// ====== INTERFACE SEGREGATION PRINCIPLE (ISP) ======
// Focused props interface for file viewing
const FileViewer = ({
  file,
  content,
  isExpanded,
  viewMode, // 'preview' or 'edit'
  onClose,
  onEdit,
  onSave,
  onDownload,
  onToggleExpand,
  onToggleViewMode,
  onContentChange
}) => {
  const [editContent, setEditContent] = useState(content || '');

  const handleSave = () => {
    onSave(editContent);
    onToggleViewMode(); // Switch back to preview mode
  };

  const handleContentChange = (e) => {
    const newContent = e.target.value;
    setEditContent(newContent);
    onContentChange?.(newContent);
  };

  const formatFileTitle = () => {
    if (file.title) return file.title;
    if (file.article_title) return file.article_title;
    if (file.name) return file.name;
    return 'Untitled File';
  };

  return (
    <div className={`flex flex-col h-full bg-white ${isExpanded ? 'fixed inset-0 z-50' : ''}`}>
      {/* ====== SINGLE RESPONSIBILITY: Toolbar rendering ====== */}
      <div className="flex-shrink-0 border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              {formatFileTitle()}
            </h2>
            {file.topic && (
              <span className="text-sm text-gray-500 truncate">
                • {file.topic}
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {viewMode === 'preview' ? (
              <Button
                variant="outline"
                size="sm"
                onClick={onEdit}
                className="flex items-center space-x-1"
              >
                <Edit className="h-4 w-4" />
                <span>Edit</span>
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={handleSave}
                className="flex items-center space-x-1 text-green-600 border-green-300 hover:bg-green-50"
              >
                <Save className="h-4 w-4" />
                <span>Save</span>
              </Button>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={onDownload}
              className="flex items-center space-x-1"
            >
              <Download className="h-4 w-4" />
              <span>Download</span>
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleExpand}
            >
              {isExpanded ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="text-red-600 border-red-300 hover:bg-red-50"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* ====== SINGLE RESPONSIBILITY: Content rendering ====== */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'edit' ? (
          <textarea
            value={editContent}
            onChange={handleContentChange}
            className="w-full h-full p-6 border-none resize-none focus:outline-none font-mono text-sm"
            placeholder="Enter markdown content..."
          />
        ) : (
          <div className="p-6">
            {content ? (
              <MarkdownContent content={content} />
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-500">No content available</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default React.memo(FileViewer); // Performance optimization