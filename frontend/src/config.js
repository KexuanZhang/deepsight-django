// Configuration file for frontend API endpoints
// This allows easy configuration for different deployment environments

// Get configuration from environment variables or use defaults
const getConfig = () => {
  // In a browser environment, these would typically be set at build time
  // For development, we use defaults
  const HOST_IP = import.meta.env.VITE_HOST_IP || 'localhost';
  const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '8000';
  
  return {
    HOST_IP,
    BACKEND_PORT,
    API_BASE_URL: `http://${HOST_IP}:${BACKEND_PORT}/api/v1`,
    BACKEND_URL: `http://${HOST_IP}:${BACKEND_PORT}`,
  };
};

export const config = {
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  // Feature flags
  USE_MINIO_URLS: import.meta.env.VITE_USE_MINIO_URLS === 'true' || true, // Enable MinIO URLs by default for testing
};

// Debug logging to verify configuration
console.log('Configuration loaded:', {
  API_BASE_URL: config.API_BASE_URL,
  USE_MINIO_URLS: config.USE_MINIO_URLS,
  VITE_USE_MINIO_URLS: import.meta.env.VITE_USE_MINIO_URLS
});

// For backward compatibility, export the API_BASE_URL directly
export const API_BASE_URL = config.API_BASE_URL;
export const BACKEND_URL = config.BACKEND_URL; 