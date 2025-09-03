import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { config } from "@/config";

interface Conference {
  id: string;
  title: string;
  description: string;
  date: string;
  location: string;
  createdAt: string;
}

interface ConferenceState {
  conferences: Conference[];
  currentConference: Conference | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: ConferenceState = {
  conferences: [],
  currentConference: null,
  isLoading: false,
  error: null,
};

export const fetchConferences = createAsyncThunk(
  'conference/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/conferences/`);
      if (!response.ok) {
        throw new Error('Failed to fetch conferences');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch conferences');
    }
  }
);

export const fetchConference = createAsyncThunk(
  'conference/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/conferences/${id}/`);
      if (!response.ok) {
        throw new Error('Failed to fetch conference');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch conference');
    }
  }
);

const conferenceSlice = createSlice({
  name: 'conference',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentConference: (state) => {
      state.currentConference = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConferences.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConferences.fulfilled, (state, action) => {
        state.isLoading = false;
        state.conferences = action.payload;
      })
      .addCase(fetchConferences.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchConference.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConference.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentConference = action.payload;
      })
      .addCase(fetchConference.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError, clearCurrentConference } = conferenceSlice.actions;
export default conferenceSlice;