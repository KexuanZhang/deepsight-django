import React from 'react';
import { Button } from '@/common/components/ui/button';
import { Settings, X } from 'lucide-react';

const AdvancedSettingsModal = ({ 
  isOpen, 
  onClose, 
  reportConfig, 
  podcastConfig,
  onReportConfigChange,
  onPodcastConfigChange, 
  availableModels 
}) => {
  if (!isOpen) return null;

  // Format model name for display
  const formatModelName = (value) => {
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white p-6 rounded-xl w-full max-w-4xl shadow-2xl max-h-[90vh] overflow-y-auto">
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

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Report Generation Settings */}
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-900 border-b pb-2">Report Generation Settings</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">AI Model</label>
                <select
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={reportConfig.model_provider || ''}
                  onChange={(e) => onReportConfigChange({ model_provider: e.target.value })}
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
                  value={reportConfig.retriever || 'searxng'}
                  onChange={(e) => onReportConfigChange({ retriever: e.target.value })}
                >
                  <option value="searxng">SearXNG</option>
                  <option value="tavily">Tavily</option>
                </select>
              </div>

              <div className="space-y-4">
                {/* Include Image Section */}
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="include-image-checkbox"
                    className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    checked={reportConfig.include_image}
                    onChange={(e) => onReportConfigChange({ include_image: e.target.checked })}
                  />
                  <label htmlFor="include-image-checkbox" className="text-sm font-medium text-gray-700 select-none">
                    Include Image
                  </label>
                </div>

                {/* White Domain Section - Only show for Tavily */}
                {reportConfig.retriever === 'tavily' && (
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="white-domain-checkbox"
                      className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      checked={reportConfig.include_domains}
                      onChange={(e) => onReportConfigChange({ include_domains: e.target.checked })}
                    />
                    <label htmlFor="white-domain-checkbox" className="text-sm font-medium text-gray-700 select-none">
                      Include Whitelist Domains
                    </label>
                  </div>
                )}
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Time Range</label>
                <select
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={reportConfig.time_range || 'ALL'}
                  onChange={(e) => onReportConfigChange({ time_range: e.target.value })}
                >
                  <option value="ALL">ALL</option>
                  <option value="day">Last 24 hours</option>
                  <option value="week">Last 7 days</option>
                  <option value="month">Last 30 days</option>
                  <option value="year">Last 365 days</option>
                </select>
              </div>
            </div>
          </div>

          {/* Panel Discussion Settings */}
          <div className="space-y-4">
            <h3 className="text-base font-semibold text-gray-900 border-b pb-2">Panel Discussion Settings</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Host Name</label>
                <input
                  type="text"
                  placeholder="e.g., 杨飞飞"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  value={podcastConfig.expert_names?.host || ''}
                  onChange={(e) => onPodcastConfigChange({ 
                    expert_names: { ...podcastConfig.expert_names, host: e.target.value }
                  })}
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Expert 1</label>
                <input
                  type="text"
                  placeholder="e.g., 奥立昆"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  value={podcastConfig.expert_names?.expert1 || ''}
                  onChange={(e) => onPodcastConfigChange({ 
                    expert_names: { ...podcastConfig.expert_names, expert1: e.target.value }
                  })}
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Expert 2</label>
                <input
                  type="text"
                  placeholder="e.g., 李特曼"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  value={podcastConfig.expert_names?.expert2 || ''}
                  onChange={(e) => onPodcastConfigChange({ 
                    expert_names: { ...podcastConfig.expert_names, expert2: e.target.value }
                  })}
                />
              </div>
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