export interface User {
  id: string;
  username: string;
  email: string;
}

export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

export type AsyncStatus = 'idle' | 'pending' | 'fulfilled' | 'rejected';