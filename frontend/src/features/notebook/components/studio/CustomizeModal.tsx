import React, { useState } from 'react';
import { Button } from "@/shared/components/ui/button";
import { Search, MessageSquare, X } from 'lucide-react';
import { COLORS } from "@/features/notebook/config/uiConfig";

interface BaseConfig {
  topic?: string;
  [key: string]: any;
}

interface FileItem {
  id: string;
  name: string;
  [key: string]: any;
}

interface CustomizeModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: BaseConfig;
  onConfigChange: (config: Partial<BaseConfig>) => void;
  type: 'report' | 'podcast';
  selectedFiles: FileItem[];
  onGenerate?: (configOverrides?: Partial<BaseConfig>) => void;
}

const CustomizeModal: React.FC<CustomizeModalProps> = ({
  isOpen,
  onClose,
  config,
  onConfigChange,
  type,
  selectedFiles,
  onGenerate
}) => {
  const [inputValue, setInputValue] = useState(config.topic || '');

  if (!isOpen) return null;

  const modalConfig = {
    report: {
      icon: Search,
      title: 'Customize Research Report',
      label: 'What should the AI focus on?',
      placeholder: 'Enter specific instructions for the research report...',
      examples: [
        "Focus on a specific source ('only cover the article about AI ethics')",
        "Focus on a specific topic ('just discuss the main findings')",
        "Target a specific audience ('explain to someone new to the field')"
      ]
    },
    podcast: {
      icon: MessageSquare,
      title: 'Customize Audio Overview', 
      label: 'What should the AI hosts focus on?',
      placeholder: 'Enter specific instructions for the AI hosts...',
      examples: [
        "Focus on a specific source ('only cover the article about Italy')",
        "Focus on a specific topic ('just discuss the novel\'s main character')",
        "Target a specific audience ('explain to someone new to biology')"
      ]
    }
  };

  const currentConfig = modalConfig[type];
  const IconComponent = currentConfig.icon;

  const hasSelectedFiles = selectedFiles.length > 0;

  const handleInputChange = (value: string) => {
    setInputValue(value);
    onConfigChange({ topic: value });
  };

  const handleGenerate = () => {
    if (hasSelectedFiles) {
      onConfigChange({ topic: inputValue });
      if (onGenerate) {
        onGenerate({ topic: inputValue });
      }
      onClose();
    }
  };

  return (
    <div className="p-6 overflow-hidden">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <IconComponent className={`h-5 w-5 ${COLORS.tw.primary.text[600]}`} />
          <h2 className="text-lg font-semibold text-gray-900">{currentConfig.title}</h2>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {currentConfig.label}
        </label>
        <textarea
          placeholder={currentConfig.placeholder}
          className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
          style={{ 
            backgroundColor: '#ffffff',
            color: '#000000',
            fontSize: '14px',
            lineHeight: '1.5',
            minHeight: '100px'
          }}
          rows={4}
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
        />
      </div>

      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Things to try:</h4>
        <ul className="space-y-2 text-sm text-gray-600">
          {currentConfig.examples.map((example, index) => (
            <li key={index} className="flex items-start space-x-2">
              <span className={`${COLORS.tw.primary.text[500]} mt-1`}>•</span>
              <span>{example}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex justify-end">
        <div className="relative group">
          <Button
            className={`px-6 py-2.5 rounded-lg transition-all duration-200 ${
              !hasSelectedFiles
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : `${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`
            }`}
            onClick={handleGenerate}
            disabled={!hasSelectedFiles}
          >
            Generate
          </Button>
          {!hasSelectedFiles && (
            <div className="absolute bottom-full right-0 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap z-10 max-w-xs">
              Select at least one source to generate
              <div className="absolute top-full right-4 border-4 border-transparent border-t-gray-800"></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CustomizeModal;