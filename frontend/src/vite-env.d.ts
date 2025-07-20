/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_HOST_IP?: string;
  readonly VITE_BACKEND_PORT?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_USE_MINIO_URLS?: string;
  // Add more environment variables as needed
}