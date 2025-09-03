import { createSlice, createAsyncThunk, createSelector } from '@reduxjs/toolkit';
import { ReportService } from './services/ReportService';
import { Report, ReportState, ReportGenerationRequest, ReportFilters, ReportContent } from "@/features/report/types/type";
import { GenerationState } from "@/shared/utils/generation";

const initialState: ReportState = {
  reports: [],
  currentReport: null,
  isLoading: false,
  error: null,
  lastFetched: null,
  searchTerm: '',
  sortOrder: 'recent',
  viewMode: 'grid',
  filters: {},
};

export const fetchReports = createAsyncThunk(
  'report/fetchAll',
  async (filters: ReportFilters | undefined, { rejectWithValue }) => {
    try {
      const reportService = new ReportService();
      const reports = await reportService.getReports(filters);
      return { data: reports, timestamp: Date.now() };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch reports');
    }
  }
);

export const fetchReport = createAsyncThunk(
  'report/fetchOne',
  async (id: string, { rejectWithValue }) => {
    try {
      const reportService = new ReportService();
      const report = await reportService.getReport(id);
      return report;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch report');
    }
  }
);

export const fetchReportContent = createAsyncThunk(
  'report/fetchContent',
  async (id: string, { rejectWithValue }) => {
    try {
      const reportService = new ReportService();
      const content = await reportService.getReportContent(id);
      return { id, content };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to fetch report content');
    }
  }
);

export const generateReport = createAsyncThunk(
  'report/generate',
  async (config: ReportGenerationRequest, { rejectWithValue }) => {
    try {
      const reportService = new ReportService(config.notebook_id);
      const response = await reportService.generateReport(config);
      return response;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to generate report');
    }
  }
);

export const cancelReport = createAsyncThunk(
  'report/cancel',
  async (id: string, { rejectWithValue }) => {
    try {
      const reportService = new ReportService();
      await reportService.cancelReport(id);
      return id;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to cancel report');
    }
  }
);

export const deleteReport = createAsyncThunk(
  'report/delete',
  async (id: string, { rejectWithValue }) => {
    try {
      const reportService = new ReportService();
      await reportService.deleteReport(id);
      return id;
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to delete report');
    }
  }
);

export const downloadReport = createAsyncThunk(
  'report/download',
  async ({ id, filename }: { id: string; filename?: string }, { rejectWithValue }) => {
    try {
      const reportService = new ReportService();
      await reportService.downloadReport(id, filename);
      return { id, filename };
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed to download report');
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
    addReportOptimistic: (state, action) => {
      state.reports.unshift(action.payload);
    },
    updateReportOptimistic: (state, action) => {
      const index = state.reports.findIndex((r: Report) => r.id === action.payload.id);
      if (index !== -1) {
        state.reports[index] = { ...state.reports[index], ...action.payload };
      }
    },
    removeReportOptimistic: (state, action) => {
      state.reports = state.reports.filter((r: Report) => r.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all reports
      .addCase(fetchReports.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchReports.fulfilled, (state, action) => {
        state.isLoading = false;
        state.reports = action.payload.data;
        state.lastFetched = action.payload.timestamp;
      })
      .addCase(fetchReports.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Fetch single report
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
      })
      
      // Generate report
      .addCase(generateReport.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(generateReport.fulfilled, (state, action) => {
        state.isLoading = false;
        // Add the new report to the list
        const newReport: Report = {
          id: action.payload.job_id,
          job_id: action.payload.job_id,
          title: 'Generating...',
          status: 'pending',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        state.reports.unshift(newReport);
      })
      .addCase(generateReport.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string;
      })
      
      // Cancel report
      .addCase(cancelReport.fulfilled, (state, action) => {
        const index = state.reports.findIndex((r: Report) => r.id === action.payload);
        if (index !== -1) {
          state.reports[index].status = 'cancelled';
        }
        if (state.currentReport?.id === action.payload) {
          state.currentReport.status = 'cancelled';
        }
      })
      
      // Delete report
      .addCase(deleteReport.fulfilled, (state, action) => {
        state.reports = state.reports.filter((r: Report) => r.id !== action.payload);
        if (state.currentReport?.id === action.payload) {
          state.currentReport = null;
        }
      });
  },
});

export const { 
  clearError, 
  clearCurrentReport, 
  setSearchTerm, 
  setSortOrder, 
  setViewMode, 
  setFilters,
  addReportOptimistic,
  updateReportOptimistic,
  removeReportOptimistic
} = reportSlice.actions;

// ====== SELECTORS ======

export const selectReports = (state: { report: ReportState }) => state.report.reports;
export const selectCurrentReport = (state: { report: ReportState }) => state.report.currentReport;
export const selectReportLoading = (state: { report: ReportState }) => state.report.isLoading;
export const selectReportError = (state: { report: ReportState }) => state.report.error;
export const selectSearchTerm = (state: { report: ReportState }) => state.report.searchTerm;
export const selectSortOrder = (state: { report: ReportState }) => state.report.sortOrder;
export const selectViewMode = (state: { report: ReportState }) => state.report.viewMode;
export const selectFilters = (state: { report: ReportState }) => state.report.filters;
export const selectLastFetched = (state: { report: ReportState }) => state.report.lastFetched;

export const selectFilteredReports = createSelector(
  [selectReports, selectSearchTerm, selectFilters, selectSortOrder],
  (reports, searchTerm, filters, sortOrder) => {
    let filtered = reports;

    // Apply search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter((report: Report) => 
        report.title?.toLowerCase().includes(searchLower) ||
        report.topic?.toLowerCase().includes(searchLower) ||
        report.content?.toLowerCase().includes(searchLower)
      );
    }

    // Apply other filters
    if (filters.status) {
      filtered = filtered.filter((report: Report) => report.status === filters.status);
    }
    if (filters.model_provider) {
      filtered = filtered.filter((report: Report) => report.model_provider === filters.model_provider);
    }
    if (filters.notebook_id) {
      filtered = filtered.filter((report: Report) => report.notebook_id === filters.notebook_id);
    }

    // Apply sorting
    switch (sortOrder) {
      case 'recent':
        return filtered.sort((a: Report, b: Report) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      case 'oldest':
        return filtered.sort((a: Report, b: Report) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      case 'title':
        return filtered.sort((a: Report, b: Report) => (a.title || '').localeCompare(b.title || ''));
      default:
        return filtered;
    }
  }
);

export const selectReportById = (id: string) =>
  createSelector(
    [selectReports],
    (reports: any[]) => reports.find((report: any) => report.id === id)
  );

export const selectReportStats = createSelector(
  [selectReports],
  (reports: any[]) => ({
    total: reports.length,
    completed: reports.filter((r: any) => r.status === 'completed').length,
    failed: reports.filter((r: any) => r.status === 'failed').length,
    pending: reports.filter((r: any) => r.status === 'pending').length,
    running: reports.filter((r: any) => r.status === 'running').length,
    cancelled: reports.filter((r: any) => r.status === 'cancelled').length,
  })
);

export default reportSlice;