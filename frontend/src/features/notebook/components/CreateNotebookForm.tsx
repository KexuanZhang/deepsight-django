import React, { useState } from "react";
import { Plus } from "lucide-react";

// Define the component props interface
interface CreateNotebookFormProps {
  onSubmit: (name: string, description: string) => Promise<{ success: boolean; error?: string }>;
  onCancel: () => void;
  loading: boolean;
  error?: string | null;
}

/**
 * Form component for creating new notebooks
 * Handles input validation and submission
 */
const CreateNotebookForm: React.FC<CreateNotebookFormProps> = ({ 
  onSubmit, 
  onCancel, 
  loading, 
  error 
}) => {
  const [name, setName] = useState<string>("");
  const [description, setDescription] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!name.trim()) return;

    const result = await onSubmit(name, description);
    if (result.success) {
      setName("");
      setDescription("");
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-lg mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Notebook</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Notebook Name *
            </label>
            <input
              type="text"
              placeholder="Enter notebook name"
              value={name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <input
              type="text"
              placeholder="Brief description (optional)"
              value={description}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDescription(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
            />
          </div>
        </div>
        
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
        
        <div className="flex items-center space-x-3">
          <button
            type="submit"
            disabled={loading || !name.trim()}
            className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 disabled:from-gray-400 disabled:to-gray-500 transition-all font-medium"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Creating...</span>
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                <span>Create Notebook</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={() => {
              onCancel();
              setName("");
              setDescription("");
            }}
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateNotebookForm;