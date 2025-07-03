import { useState, useCallback } from 'react';
import { config } from '../../../config';

/**
 * Custom hook for notebook data management
 * Handles notebook CRUD operations and metadata
 */
export const useNotebookData = () => {
  const [notebooks, setNotebooks] = useState([]);
  const [currentNotebook, setCurrentNotebook] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Helper to read CSRF token from cookies
  const getCookie = useCallback((name) => {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  }, []);

  // Prime CSRF token
  const primeCsrf = useCallback(async () => {
    try {
      await fetch(`${config.API_BASE_URL}/users/csrf/`, {
        method: "GET",
        credentials: "include",
      });
    } catch (error) {
      console.error('Failed to prime CSRF:', error);
    }
  }, []);

  // Fetch all notebooks
  const fetchNotebooks = useCallback(async (sortOrder = "recent") => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/`, { 
        credentials: "include" 
      });
      
      if (response.status === 401) {
        throw new Error('Unauthorized');
      }
      
      if (!response.ok) {
        throw new Error('Failed to fetch notebooks');
      }
      
      let data = await response.json();
      
      // Sort notebooks
      data.sort((a, b) => {
        const aT = new Date(a.created_at).getTime();
        const bT = new Date(b.created_at).getTime();
        return sortOrder === "recent" ? bT - aT : aT - bT;
      });
      
      setNotebooks(data);
      return { success: true, data };
    } catch (err) {
      const errorMessage = err.message === 'Unauthorized' ? err.message : "Unable to load notebooks.";
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch single notebook
  const fetchNotebook = useCallback(async (notebookId) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/${notebookId}/`, {
        credentials: "include",
      });

      if (response.status === 401) {
        throw new Error('Unauthorized');
      }
      
      if (response.status === 404) {
        throw new Error('Notebook not found');
      }
      
      if (!response.ok) {
        throw new Error('Failed to load notebook data');
      }

      const data = await response.json();
      setCurrentNotebook(data);
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, []);

  // Create new notebook
  const createNotebook = useCallback(async (name, description) => {
    if (!name.trim()) {
      throw new Error('Name is required');
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim(),
        }),
      });

      if (response.status === 401) {
        throw new Error('Unauthorized');
      }

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to create notebook");
      }

      const data = await response.json();
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getCookie]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Delete notebook
  const deleteNotebook = useCallback(async (notebookId) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/${notebookId}/`, {
        method: "DELETE",
        credentials: "include",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });

      if (response.status === 401) {
        throw new Error('Unauthorized');
      }

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || "Failed to delete notebook");
      }

      // Remove notebook from local state
      setNotebooks(prev => prev.filter(nb => nb.id !== notebookId));
      
      // Clear current notebook if it was deleted
      if (currentNotebook?.id === notebookId) {
        setCurrentNotebook(null);
      }
      
      return { success: true };
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getCookie, currentNotebook]);

  // Clear current notebook
  const clearCurrentNotebook = useCallback(() => {
    setCurrentNotebook(null);
  }, []);

  return {
    notebooks,
    currentNotebook,
    loading,
    error,
    fetchNotebooks,
    fetchNotebook,
    createNotebook,
    deleteNotebook,
    primeCsrf,
    clearError,
    clearCurrentNotebook,
  };
};