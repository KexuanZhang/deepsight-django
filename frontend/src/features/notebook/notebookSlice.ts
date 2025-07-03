import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { config } from '../../config';

interface Notebook {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  updatedAt: string;
}

interface NotebookState {
  notebooks: Notebook[];
  currentNotebook: Notebook | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: NotebookState = {
  notebooks: [],
  currentNotebook: null,
  isLoading: false,
  error: null,
};

export const fetchNotebooks = createAsyncThunk(
  'notebook/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/`);
      if (!response.ok) {
        throw new Error('Failed to fetch notebooks');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch notebooks');
    }
  }
);

export const fetchNotebook = createAsyncThunk(
  'notebook/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/${id}/`);
      if (!response.ok) {
        throw new Error('Failed to fetch notebook');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch notebook');
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
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchNotebooks.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchNotebooks.fulfilled, (state, action) => {
        state.isLoading = false;
        state.notebooks = action.payload;
      })
      .addCase(fetchNotebooks.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
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
      });
  },
});

export const { clearError, clearCurrentNotebook } = notebookSlice.actions;
export default notebookSlice;