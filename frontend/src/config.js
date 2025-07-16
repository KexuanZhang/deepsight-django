// Configuration file for frontend API endpoints
// This allows easy configuration for different deployment environments

// Get configuration from environment variables or use defaults
const getConfig = () => {
  // In a browser environment, these would typically be set at build time
  // For development, we use defaults
  const HOST_IP = import.meta.env.VITE_HOST_IP || 'localhost';
  const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '8001';
  
  return {
    HOST_IP,
    BACKEND_PORT,
    API_BASE_URL: `http://${HOST_IP}:${BACKEND_PORT}/api/v1`,
    BACKEND_URL: `http://${HOST_IP}:${BACKEND_PORT}`,
  };
};

export const config = getConfig();

// For backward compatibility, export the API_BASE_URL directly
export const API_BASE_URL = config.API_BASE_URL;
export const BACKEND_URL = config.BACKEND_URL; 