// Configuration file for frontend API endpoints
// This allows easy configuration for different deployment environments

/// <reference types="vite/client" />

// Configuration interface
interface Config {
  HOST_IP: string;
  BACKEND_PORT: string;
  API_BASE_URL: string;
  BACKEND_URL: string;
}

// App configuration interface
interface AppConfig {
  API_BASE_URL: string;
  USE_MINIO_URLS: boolean;
}

// Get configuration from environment variables or use defaults
const getConfig = (): Config => {
  // In a browser environment, these would typically be set at build time
  // For development, we use defaults
  // @ts-ignore - Vite handles import.meta.env at build time
  const HOST_IP = import.meta.env.VITE_HOST_IP || 'localhost';
  // @ts-ignore - Vite handles import.meta.env at build time
  const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '8000';
  
  return {
    HOST_IP,
    BACKEND_PORT,
    API_BASE_URL: `http://${HOST_IP}:${BACKEND_PORT}/api/v1`,
    BACKEND_URL: `http://${HOST_IP}:${BACKEND_PORT}`,
  };
};

export const config: AppConfig = {
  // @ts-ignore - Vite handles import.meta.env at build time
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  // Feature flags
  // @ts-ignore - Vite handles import.meta.env at build time
  USE_MINIO_URLS: import.meta.env.VITE_USE_MINIO_URLS === 'true' || true, // Enable MinIO URLs by default for testing
};

// Debug logging to verify configuration
console.log('Configuration loaded:', {
  API_BASE_URL: config.API_BASE_URL,
  USE_MINIO_URLS: config.USE_MINIO_URLS,
  // @ts-ignore - Vite handles import.meta.env at build time
  VITE_USE_MINIO_URLS: import.meta.env.VITE_USE_MINIO_URLS
});

// For backward compatibility, export the API_BASE_URL directly
export const API_BASE_URL: string = config.API_BASE_URL;
export const BACKEND_URL: string = getConfig().BACKEND_URL; 