import { createSlice, createAsyncThunk, createSelector } from '@reduxjs/toolkit';
import { PodcastService } from './services/PodcastService';
import { Podcast, PodcastState, PodcastGenerationRequest, PodcastFilters, PodcastAudio } from "@/features/podcast/types/type";
import { GenerationState } from "@/shared/utils/generation";

const initialState: PodcastState = {
  podcasts: [],
  currentPodcast: null,
  isLoading: false,
  error: null,
  lastFetched: null,
  searchTerm: '',
  sortOrder: 'recent',
  viewMode: 'grid',
  filters: {},
};

export const fetchPodcasts = createAsyncThunk(
  'podcast/fetchAll',
  async (filters: PodcastFilters | undefined, { rejectWithValue }) => {
    try {
      const podcastService = new PodcastService();
      const podcasts = await podcastService.getPodcasts(filters);
      return { data: podcasts, timestamp: Date.now() };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch podcasts');
    }
  }
);

export const fetchPodcast = createAsyncThunk(
  'podcast/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const podcastService = new PodcastService();
      const podcast = await podcastService.getPodcast(id);
      return podcast;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch podcast');
    }
  }
);

export const fetchPodcastAudio = createAsyncThunk(
  'podcast/fetchAudio',
  async (id: string, { rejectWithValue }) => {
    try {
      const podcastService = new PodcastService();
      const audio = await podcastService.getPodcastAudio(id);
      return { id, audio };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch podcast audio');
    }
  }
);

export const generatePodcast = createAsyncThunk(
  'podcast/generate',
  async (config: PodcastGenerationRequest, { rejectWithValue }) => {
    try {
      const podcastService = new PodcastService(config.notebook_id);
      const response = await podcastService.generatePodcast(config);
      return response;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to generate podcast');
    }
  }
);

export const cancelPodcast = createAsyncThunk(
  'podcast/cancel',
  async (id: string, { rejectWithValue }) => {
    try {
      const podcastService = new PodcastService();
      await podcastService.cancelPodcast(id);
      return id;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to cancel podcast');
    }
  }
);

export const deletePodcast = createAsyncThunk(
  'podcast/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      const podcastService = new PodcastService();
      await podcastService.deletePodcast(id);
      return id;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to delete podcast');
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
    setSearchTerm: (state, action) => {
      state.searchTerm = action.payload;
    },
    setSortOrder: (state, action) => {
      state.sortOrder = action.payload;
    },
    setViewMode: (state, action) => {
      state.viewMode = action.payload;
    },
    setFilters: (state, action) => {
      state.filters = action.payload;
    },
    addPodcastOptimistic: (state, action) => {
      state.podcasts.unshift(action.payload);
    },
    updatePodcastOptimistic: (state, action) => {
      const index = state.podcasts.findIndex((p: any) => p.id === action.payload.id);
      if (index !== -1) {
        state.podcasts[index] = { ...state.podcasts[index], ...action.payload };
      }
    },
    removePodcastOptimistic: (state, action) => {
      state.podcasts = state.podcasts.filter((p: any) => p.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all podcasts
      .addCase(fetchPodcasts.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchPodcasts.fulfilled, (state, action) => {
        state.isLoading = false;
        state.podcasts = action.payload.data;
        state.lastFetched = action.payload.timestamp;
      })
      .addCase(fetchPodcasts.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Fetch single podcast
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
      })
      
      // Generate podcast
      .addCase(generatePodcast.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(generatePodcast.fulfilled, (state, action) => {
        state.isLoading = false;
        // Add the new podcast to the list
        const newPodcast: Podcast = {
          id: action.payload.job_id,
          job_id: action.payload.job_id,
          title: 'Generating...',
          status: 'pending',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        state.podcasts.unshift(newPodcast);
      })
      .addCase(generatePodcast.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Cancel podcast
      .addCase(cancelPodcast.fulfilled, (state, action) => {
        const index = state.podcasts.findIndex((p: any) => p.id === action.payload);
        if (index !== -1) {
          state.podcasts[index].status = 'cancelled';
        }
        if (state.currentPodcast?.id === action.payload) {
          state.currentPodcast.status = 'cancelled';
        }
      })
      
      // Delete podcast
      .addCase(deletePodcast.fulfilled, (state, action) => {
        state.podcasts = state.podcasts.filter((p: any) => p.id !== action.payload);
        if (state.currentPodcast?.id === action.payload) {
          state.currentPodcast = null;
        }
      });
  },
});

export const { 
  clearError, 
  clearCurrentPodcast, 
  setSearchTerm, 
  setSortOrder, 
  setViewMode, 
  setFilters,
  addPodcastOptimistic,
  updatePodcastOptimistic,
  removePodcastOptimistic
} = podcastSlice.actions;

// ====== SELECTORS ======

export const selectPodcasts = (state: { podcast: PodcastState }) => state.podcast.podcasts;
export const selectCurrentPodcast = (state: { podcast: PodcastState }) => state.podcast.currentPodcast;
export const selectPodcastLoading = (state: { podcast: PodcastState }) => state.podcast.isLoading;
export const selectPodcastError = (state: { podcast: PodcastState }) => state.podcast.error;
export const selectSearchTerm = (state: { podcast: PodcastState }) => state.podcast.searchTerm;
export const selectSortOrder = (state: { podcast: PodcastState }) => state.podcast.sortOrder;
export const selectViewMode = (state: { podcast: PodcastState }) => state.podcast.viewMode;
export const selectFilters = (state: { podcast: PodcastState }) => state.podcast.filters;
export const selectLastFetched = (state: { podcast: PodcastState }) => state.podcast.lastFetched;

export const selectFilteredPodcasts = createSelector(
  [selectPodcasts, selectSearchTerm, selectFilters, selectSortOrder],
  (podcasts, searchTerm, filters, sortOrder) => {
    let filtered = podcasts;

    // Apply search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(podcast => 
        podcast.title?.toLowerCase().includes(searchLower) ||
        podcast.topic?.toLowerCase().includes(searchLower) ||
        podcast.description?.toLowerCase().includes(searchLower)
      );
    }

    // Apply other filters
    if (filters.status) {
      filtered = filtered.filter(podcast => podcast.status === filters.status);
    }
    if (filters.notebook_id) {
      filtered = filtered.filter(podcast => podcast.notebook_id === filters.notebook_id);
    }

    // Apply sorting
    switch (sortOrder) {
      case 'recent':
        return filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      case 'oldest':
        return filtered.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      case 'title':
        return filtered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
      default:
        return filtered;
    }
  }
);

export const selectPodcastById = (id: string) =>
  createSelector(
    [selectPodcasts],
    (podcasts) => podcasts.find(podcast => podcast.id === id)
  );

export const selectPodcastStats = createSelector(
  [selectPodcasts],
  (podcasts) => ({
    total: podcasts.length,
    completed: podcasts.filter((p: any) => p.status === 'completed').length,
    failed: podcasts.filter((p: any) => p.status === 'failed').length,
    pending: podcasts.filter((p: any) => p.status === 'pending').length,
    generating: podcasts.filter((p: any) => p.status === 'generating').length,
    cancelled: podcasts.filter((p: any) => p.status === 'cancelled').length,
  })
);

export default podcastSlice;