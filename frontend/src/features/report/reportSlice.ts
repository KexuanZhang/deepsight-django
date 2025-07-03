import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

interface Report {
  id: string;
  title: string;
  description: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

interface ReportState {
  reports: Report[];
  currentReport: Report | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: ReportState = {
  reports: [],
  currentReport: null,
  isLoading: false,
  error: null,
};

export const fetchReports = createAsyncThunk(
  'report/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/reports/');
      if (!response.ok) {
        throw new Error('Failed to fetch reports');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch reports');
    }
  }
);

export const fetchReport = createAsyncThunk(
  'report/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const response = await fetch(`/api/reports/${id}/`);
      if (!response.ok) {
        throw new Error('Failed to fetch report');
      }
      return await response.json();
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch report');
    }
  }
);

const reportSlice = createSlice({
  name: 'report',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearCurrentReport: (state) => {
      state.currentReport = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchReports.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchReports.fulfilled, (state, action) => {
        state.isLoading = false;
        state.reports = action.payload;
      })
      .addCase(fetchReports.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchReport.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchReport.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentReport = action.payload;
      })
      .addCase(fetchReport.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError, clearCurrentReport } = reportSlice.actions;
export default reportSlice;