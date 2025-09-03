import { combineReducers } from '@reduxjs/toolkit';
import authSlice from "@/features/auth/authSlice";
import dashboardSlice from "@/features/dashboard/dashboardSlice";
import conferenceSlice from "@/features/conference/conferenceSlice";
import notebookSlice from "@/features/notebook/notebookSlice";
import podcastSlice from "@/features/podcast/podcastSlice";
import reportSlice from "@/features/report/reportSlice";

const rootReducer = combineReducers({
  auth: authSlice.reducer,
  dashboard: dashboardSlice.reducer,
  conference: conferenceSlice.reducer,
  notebook: notebookSlice.reducer,
  podcast: podcastSlice.reducer,
  report: reportSlice.reducer,
});

export default rootReducer;