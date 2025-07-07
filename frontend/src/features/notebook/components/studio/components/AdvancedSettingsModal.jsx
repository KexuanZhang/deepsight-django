import React from 'react';
import { Button } from '@/common/components/ui/button';
import { Settings, X } from 'lucide-react';

const AdvancedSettingsModal = ({ 
  isOpen, 
  onClose, 
  config, 
  onConfigChange, 
  availableModels 
}) => {
  if (!isOpen) return null;

  // Format model name for display
  const formatModelName = (value) => {
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center">
      <div className="bg-white p-6 rounded-lg w-[600px] shadow-lg max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-2">
            <Settings className="h-5 w-5 text-gray-600" />
            <h2 className="text-lg font-semibold text-gray-900">Advanced Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6">
          {/* Model and Search Engine Section */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">AI Model</label>
                <select
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={config.model_provider || ''}
                  onChange={(e) => onConfigChange({ model_provider: e.target.value })}
                >
                  {(availableModels?.model_providers || []).map(provider => (
                    <option key={provider} value={provider}>
                      {formatModelName(provider)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Search Engine</label>
                <select
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={config.retriever || 'searxng'}
                  onChange={(e) => onConfigChange({ retriever: e.target.value })}
                >
                  <option value="searxng">SearXNG</option>
                  <option value="tavily">Tavily</option>
                </select>
              </div>
            </div>

            {/* Include Image Section */}
            <div className="flex items-center space-x-2 pt-2">
              <input
                type="checkbox"
                id="include-image-checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                checked={config.include_image}
                onChange={(e) => onConfigChange({ include_image: e.target.checked })}
              />
              <label htmlFor="include-image-checkbox" className="text-sm font-medium text-gray-700 select-none">
                Include Image
              </label>
            </div>

            {/* White Domain Section */}
            <div className="flex items-center space-x-2 pt-2">
              <input
                type="checkbox"
                id="white-domain-checkbox"
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                checked={config.include_domains}
                onChange={(e) => onConfigChange({ include_domains: e.target.checked })}
              />
              <label htmlFor="white-domain-checkbox" className="text-sm font-medium text-gray-700 select-none">
                White Domain
              </label>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 mt-6 pt-4 border-t">
          <Button
            variant="outline"
            onClick={onClose}
            className="text-gray-600 hover:text-gray-800"
          >
            Cancel
          </Button>
          <Button
            onClick={onClose}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Save Settings
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AdvancedSettingsModal;