import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { config } from "@/config";

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isCheckingAuth: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  token: null, // Not used in session-based auth
  isAuthenticated: false,
  isLoading: false,
  isCheckingAuth: false,
  error: null,
};

export const checkCurrentUser = createAsyncThunk<User, void>(
  'auth/checkCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      // Use a completely silent approach
      const testUrl = `${config.API_BASE_URL}/users/me/`;
      
      return new Promise((resolve, reject) => {
        // Create a fetch request but intercept console errors
        const originalError = console.error;
        const originalLog = console.log;
        const originalWarn = console.warn;
        
        // Temporarily suppress console output
        console.error = () => {};
        console.log = () => {};
        console.warn = () => {};
        
        fetch(testUrl, {
          method: 'GET',
          credentials: 'include',
        })
        .then(response => {
          // Restore console
          console.error = originalError;
          console.log = originalLog;
          console.warn = originalWarn;
          
          if (response.ok) {
            return response.json();
          } else {
            throw new Error('Not authenticated');
          }
        })
        .then(data => {
          resolve(data);
        })
        .catch(() => {
          // Restore console
          console.error = originalError;
          console.log = originalLog;
          console.warn = originalWarn;
          
          reject(rejectWithValue(null));
        });
      });
    } catch (error) {
      return rejectWithValue(null);
    }
  }
);

export const loginUser = createAsyncThunk(
  'auth/login',
  async (credentials: { username: string; password: string }, { rejectWithValue }) => {
    try {
      // Helper function to get CSRF token from cookies
      const getCookie = (name: string) => {
        const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
        const value = match?.[2];
        return value ? decodeURIComponent(value) : null;
      };

      const response = await fetch(`${config.API_BASE_URL}/users/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken') || '',
        },
        credentials: 'include', // Include credentials for session-based auth
        body: JSON.stringify(credentials),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Login failed');
    }
  }
);

export const signupUser = createAsyncThunk(
  'auth/signup',
  async (userData: { username: string; email: string; password: string }, { rejectWithValue }) => {
    try {
      // Helper function to get CSRF token from cookies
      const getCookie = (name: string) => {
        const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
        const value = match?.[2];
        return value ? decodeURIComponent(value) : null;
      };

      const response = await fetch(`${config.API_BASE_URL}/users/signup/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken') || '',
        },
        credentials: 'include', // Include credentials for session-based auth
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Signup failed');
      }

      const data = await response.json();
      return data;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Signup failed');
    }
  }
);

export const logoutUser = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      // Helper function to get CSRF token from cookies
      const getCookie = (name: string) => {
        const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
        const value = match?.[2];
        return value ? decodeURIComponent(value) : null;
      };

      const response = await fetch(`${config.API_BASE_URL}/users/logout/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'X-CSRFToken': getCookie('csrftoken') || '',
        },
      });

      if (!response.ok) {
        throw new Error('Logout failed');
      }

      return true;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Logout failed');
    }
  }
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      // No localStorage manipulation needed for session-based auth
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(checkCurrentUser.pending, (state) => {
        state.isCheckingAuth = true;
      })
      .addCase(checkCurrentUser.fulfilled, (state, action) => {
        state.isCheckingAuth = false;
        state.user = action.payload;
        state.isAuthenticated = true;
        state.error = null;
      })
      .addCase(checkCurrentUser.rejected, (state) => {
        state.isCheckingAuth = false;
        state.user = null;
        state.isAuthenticated = false;
      })
      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload; // Backend returns user data directly
        state.isAuthenticated = true;
        // No token needed for session-based auth
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(signupUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(signupUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload; // Backend returns user data directly
        state.isAuthenticated = true;
        // No token needed for session-based auth
      })
      .addCase(signupUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(logoutUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.isLoading = false;
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
      })
      .addCase(logoutUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
        // Even if logout fails on server, clear local state to be safe
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
      });
  },
});

export const { logout, clearError } = authSlice.actions;
export default authSlice;