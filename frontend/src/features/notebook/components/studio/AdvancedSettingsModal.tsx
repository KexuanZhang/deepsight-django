import React, { useEffect, useState } from 'react';
import { Button } from "@/shared/components/ui/button";
import { Settings, X } from 'lucide-react';
import { COLORS } from "@/features/notebook/config/uiConfig";

interface ReportConfig {
  model_provider?: string;
  retriever?: string;
  include_image?: boolean;
  include_domains?: boolean;
  time_range?: string;
  [key: string]: any;
}

interface PodcastConfig {
  expert_names?: {
    host?: string;
    expert1?: string;
    expert2?: string;
  };
  [key: string]: any;
}

interface AvailableModels {
  model_providers?: string[];
  [key: string]: any;
}

interface AdvancedSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportConfig: ReportConfig;
  podcastConfig: PodcastConfig;
  onReportConfigChange: (updates: Partial<ReportConfig>) => void;
  onPodcastConfigChange: (updates: Partial<PodcastConfig>) => void;
  availableModels: AvailableModels;
}

const AdvancedSettingsModal: React.FC<AdvancedSettingsModalProps> = ({ 
  isOpen, 
  onClose, 
  reportConfig, 
  podcastConfig,
  onReportConfigChange,
  onPodcastConfigChange, 
  availableModels 
}) => {
  // Local state for temporary changes (only applied on save)
  const [localReportConfig, setLocalReportConfig] = useState(reportConfig);
  const [localPodcastConfig, setLocalPodcastConfig] = useState(podcastConfig);
  
  // Store original values to revert on cancel
  const [originalReportConfig, setOriginalReportConfig] = useState(reportConfig);
  const [originalPodcastConfig, setOriginalPodcastConfig] = useState(podcastConfig);

  // Update local state when modal opens (when isOpen becomes true)
  useEffect(() => {
    if (isOpen) {
      setLocalReportConfig(reportConfig);
      setLocalPodcastConfig(podcastConfig);
      setOriginalReportConfig(reportConfig);
      setOriginalPodcastConfig(podcastConfig);
    }
  }, [isOpen, reportConfig, podcastConfig]);

  if (!isOpen) return null;

  // Format model name for display
  const formatModelName = (value: string): string => {
    return value.charAt(0).toUpperCase() + value.slice(1);
  };

  // Handle report config changes (only update local state, not parent)
  const handleReportConfigChange = (updates: Partial<ReportConfig>) => {
    const newConfig = { ...localReportConfig, ...updates };
    setLocalReportConfig(newConfig);
  };

  // Handle podcast config changes (only update local state, not parent)
  const handlePodcastConfigChange = (updates: Partial<PodcastConfig>) => {
    const newConfig = { ...localPodcastConfig, ...updates };
    setLocalPodcastConfig(newConfig);
  };

  // Handle save - apply changes to parent state
  const handleSave = () => {
    // Calculate what changed and send only those updates
    const reportUpdates: Partial<ReportConfig> = {};
    const podcastUpdates: Partial<PodcastConfig> = {};
    
    // Check report config changes
    (Object.keys(localReportConfig) as Array<keyof ReportConfig>).forEach(key => {
      if (localReportConfig[key] !== originalReportConfig[key]) {
        reportUpdates[key] = localReportConfig[key];
      }
    });
    
    // Check podcast config changes
    (Object.keys(localPodcastConfig) as Array<keyof PodcastConfig>).forEach(key => {
      if (JSON.stringify(localPodcastConfig[key]) !== JSON.stringify(originalPodcastConfig[key])) {
        podcastUpdates[key] = localPodcastConfig[key];
      }
    });
    
    // Apply updates if there are any changes
    if (Object.keys(reportUpdates).length > 0) {
      onReportConfigChange(reportUpdates);
    }
    
    if (Object.keys(podcastUpdates).length > 0) {
      onPodcastConfigChange(podcastUpdates);
    }
    
    onClose();
  };

  // Handle cancel - revert to original values
  const handleCancel = () => {
    setLocalReportConfig(originalReportConfig);
    setLocalPodcastConfig(originalPodcastConfig);
    onClose();
  };

    return (
    <>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Settings className="h-5 w-5 text-gray-600" />
          <h2 className="text-lg font-semibold text-gray-900">Advanced Settings</h2>
        </div>
        <button
          onClick={handleCancel}
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
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                  value={localReportConfig.model_provider || ''}
                  onChange={(e) => handleReportConfigChange({ model_provider: e.target.value })}
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
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                  value={localReportConfig.retriever || 'searxng'}
                  onChange={(e) => handleReportConfigChange({ 
                    retriever: e.target.value,
                    include_domains: e.target.value === 'tavily' ? true : localReportConfig.include_domains
                  })}
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
                    className="h-4 w-4 accent-red-500 border-gray-300 rounded focus:ring-red-500 focus:outline-none"
                    checked={localReportConfig.include_image}
                    onChange={(e) => handleReportConfigChange({ include_image: e.target.checked })}
                  />
                  <label htmlFor="include-image-checkbox" className="text-sm font-medium text-gray-700 select-none">
                    Include Image
                  </label>
                </div>

                {/* White Domain Section - Only show for Tavily */}
                {localReportConfig.retriever === 'tavily' && (
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="white-domain-checkbox"
                      className="h-4 w-4 accent-red-500 border-gray-300 rounded focus:ring-red-500 focus:outline-none"
                      checked={localReportConfig.include_domains}
                      onChange={(e) => handleReportConfigChange({ include_domains: e.target.checked })}
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
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                  value={localReportConfig.time_range || 'ALL'}
                  onChange={(e) => handleReportConfigChange({ time_range: e.target.value })}
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
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                  value={localPodcastConfig.expert_names?.host || ''}
                  onChange={(e) => handlePodcastConfigChange({ 
                    expert_names: { ...localPodcastConfig.expert_names, host: e.target.value }
                  })}
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Expert 1</label>
                <input
                  type="text"
                  placeholder="e.g., 奥立昆"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                  value={localPodcastConfig.expert_names?.expert1 || ''}
                  onChange={(e) => handlePodcastConfigChange({ 
                    expert_names: { ...localPodcastConfig.expert_names, expert1: e.target.value }
                  })}
                />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Expert 2</label>
                <input
                  type="text"
                  placeholder="e.g., 李特曼"
                  className="w-full p-3 border border-gray-300 rounded-lg text-sm accent-red-500 focus:ring-2 focus:ring-red-500 focus:border-transparent focus:outline-none"
                  value={localPodcastConfig.expert_names?.expert2 || ''}
                  onChange={(e) => handlePodcastConfigChange({ 
                    expert_names: { ...localPodcastConfig.expert_names, expert2: e.target.value }
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
            onClick={handleCancel}
            className="text-gray-600 hover:text-gray-800"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            className={`${COLORS.tw.primary.bg[600]} ${COLORS.tw.primary.hover.bg[700]} text-white`}
          >
            Save Settings
          </Button>
        </div>
    </>
  );
};

export default AdvancedSettingsModal;