import { createSlice, createAsyncThunk, createSelector } from '@reduxjs/toolkit';
import notebookService from './services/NotebookService';
import type { 
  Notebook, 
  NotebookState, 
  CreateNotebookRequest, 
  UpdateNotebookRequest,
  SortOrder,
  ViewMode
} from "@/features/notebook/type";

const initialState: NotebookState = {
  notebooks: [],
  currentNotebook: null,
  isLoading: false,
  error: null,
  lastFetched: null,
  searchTerm: '',
  sortOrder: 'recent',
  viewMode: 'grid',
};

// Enhanced async thunks with better error handling
export const fetchNotebooks = createAsyncThunk(
  'notebook/fetchAll',
  async (_, { rejectWithValue, getState }) => {
    try {
      const data = await notebookService.getNotebooks();
      return { data, timestamp: Date.now() };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch notebooks');
    }
  }
);

export const fetchNotebook = createAsyncThunk(
  'notebook/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const data = await notebookService.getNotebook(id);
      return data;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch notebook');
    }
  }
);

export const createNotebook = createAsyncThunk(
  'notebook/create',
  async ({ name, description }: { name: string; description: string }, { rejectWithValue }) => {
    try {
      const data = await notebookService.createNotebook(name, description);
      return data;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to create notebook');
    }
  }
);

export const updateNotebook = createAsyncThunk(
  'notebook/update',
  async ({ id, updates }: { id: string; updates: UpdateNotebookRequest }, { rejectWithValue }) => {
    try {
      const data = await notebookService.updateNotebook(id, updates);
      return { ...data };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to update notebook');
    }
  }
);

export const deleteNotebook = createAsyncThunk(
  'notebook/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      await notebookService.deleteNotebook(id);
      return id;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to delete notebook');
    }
  }
);

const notebookSlice = createSlice({
  name: 'notebook',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentNotebook: (state) => {
      state.currentNotebook = null;
    },
    setSearchTerm: (state, action) => {
      state.searchTerm = action.payload;
    },
    setSortOrder: (state, action) => {
      state.sortOrder = action.payload;
    },
    setViewMode: (state, action) => {
      state.viewMode = action.payload;
    },
    // Optimistic updates
    addNotebookOptimistic: (state, action) => {
      state.notebooks.unshift(action.payload);
    },
    updateNotebookOptimistic: (state, action) => {
      const index = state.notebooks.findIndex(n => n.id === action.payload.id);
      if (index !== -1) {
        state.notebooks[index] = { ...state.notebooks[index], ...action.payload };
      }
    },
    removeNotebookOptimistic: (state, action) => {
      state.notebooks = state.notebooks.filter(n => n.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all notebooks
      .addCase(fetchNotebooks.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchNotebooks.fulfilled, (state, action) => {
        state.isLoading = false;
        state.notebooks = action.payload.data;
        state.lastFetched = action.payload.timestamp;
      })
      .addCase(fetchNotebooks.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Fetch single notebook
      .addCase(fetchNotebook.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchNotebook.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentNotebook = action.payload;
      })
      .addCase(fetchNotebook.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Create notebook
      .addCase(createNotebook.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(createNotebook.fulfilled, (state, action) => {
        state.isLoading = false;
        state.notebooks.unshift(action.payload);
      })
      .addCase(createNotebook.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Update notebook
      .addCase(updateNotebook.fulfilled, (state, action) => {
        const index = state.notebooks.findIndex(n => n.id === action.payload.id);
        if (index !== -1) {
          state.notebooks[index] = action.payload;
        }
        if (state.currentNotebook?.id === action.payload.id) {
          state.currentNotebook = action.payload;
        }
      })
      .addCase(updateNotebook.rejected, (state, action) => {
        state.error = action.payload as string;
      })
      
      // Delete notebook
      .addCase(deleteNotebook.fulfilled, (state, action) => {
        state.notebooks = state.notebooks.filter(n => n.id !== action.payload);
        if (state.currentNotebook?.id === action.payload) {
          state.currentNotebook = null;
        }
      })
      .addCase(deleteNotebook.rejected, (state, action) => {
        state.error = action.payload as string;
      });
  },
});

// Enhanced selectors with memoization
export const selectNotebooks = (state: { notebook: NotebookState }) => state.notebook.notebooks;
export const selectCurrentNotebook = (state: { notebook: NotebookState }) => state.notebook.currentNotebook;
export const selectNotebookLoading = (state: { notebook: NotebookState }) => state.notebook.isLoading;
export const selectNotebookError = (state: { notebook: NotebookState }) => state.notebook.error;
export const selectSearchTerm = (state: { notebook: NotebookState }) => state.notebook.searchTerm;
export const selectSortOrder = (state: { notebook: NotebookState }) => state.notebook.sortOrder;
export const selectViewMode = (state: { notebook: NotebookState }) => state.notebook.viewMode;

// Memoized filtered and sorted notebooks selector
export const selectFilteredNotebooks = createSelector(
  [selectNotebooks, selectSearchTerm, selectSortOrder],
  (notebooks, searchTerm, sortOrder) => {
    let filtered = notebooks;
    
    // Apply search filter
    if (searchTerm) {
      const lowerSearchTerm = searchTerm.toLowerCase();
      filtered = notebooks.filter(notebook =>
        notebook.name.toLowerCase().includes(lowerSearchTerm) ||
        (notebook.description && notebook.description.toLowerCase().includes(lowerSearchTerm))
      );
    }
    
    // Apply sorting
    return filtered.sort((a, b) => {
      const aTime = new Date(a.created_at).getTime();
      const bTime = new Date(b.created_at).getTime();
      return sortOrder === 'recent' ? bTime - aTime : aTime - bTime;
    });
  }
);

// Selector for notebook by ID
export const selectNotebookById = (id: string) =>
  createSelector(
    [selectNotebooks],
    (notebooks) => notebooks.find(notebook => notebook.id === id)
  );

// Selector for notebooks count
export const selectNotebooksCount = createSelector(
  [selectNotebooks],
  (notebooks) => notebooks.length
);

// Selector for recent notebooks (last 7 days)
export const selectRecentNotebooks = createSelector(
  [selectNotebooks],
  (notebooks) => {
    const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    return notebooks.filter(notebook => 
      new Date(notebook.created_at).getTime() > sevenDaysAgo
    );
  }
);

// Data freshness selector
export const selectDataFreshness = (state: { notebook: NotebookState }) => {
  const { lastFetched } = state.notebook;
  if (!lastFetched) return 'stale';
  
  const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
  return lastFetched > fiveMinutesAgo ? 'fresh' : 'stale';
};

export const { 
  clearError, 
  clearCurrentNotebook, 
  setSearchTerm, 
  setSortOrder, 
  setViewMode,
  addNotebookOptimistic,
  updateNotebookOptimistic,
  removeNotebookOptimistic
} = notebookSlice.actions;

export default notebookSlice;