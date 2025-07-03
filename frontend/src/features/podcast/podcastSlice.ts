import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { config } from '../../config';

interface Podcast {
  id: string;
  title: string;
  description: string;
  audioUrl: string;
  duration: number;
  createdAt: string;
}

interface PodcastState {
  podcasts: Podcast[];
  currentPodcast: Podcast | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: PodcastState = {
  podcasts: [],
  currentPodcast: null,
  isLoading: false,
  error: null,
};

export const fetchPodcasts = createAsyncThunk(
  'podcast/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/podcasts/`);
      if (!response.ok) {
        throw new Error('Failed to fetch podcasts');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch podcasts');
    }
  }
);

export const fetchPodcast = createAsyncThunk(
  'podcast/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/podcasts/${id}/`);
      if (!response.ok) {
        throw new Error('Failed to fetch podcast');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch podcast');
    }
  }
);

const podcastSlice = createSlice({
  name: 'podcast',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentPodcast: (state) => {
      state.currentPodcast = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPodcasts.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchPodcasts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.podcasts = action.payload;
      })
      .addCase(fetchPodcasts.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchPodcast.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchPodcast.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentPodcast = action.payload;
      })
      .addCase(fetchPodcast.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError, clearCurrentPodcast } = podcastSlice.actions;
export default podcastSlice;