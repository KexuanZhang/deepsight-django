import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from '@/app/store';
import HomePage from '@/common/components/HomePage';
import DatasetPage from '@/common/components/DatasetPage';
import DeepdivePage from '@/features/notebook/DeepdivePage';
import DashboardPage from '@/features/dashboard/DashboardPage';
import LoginPage from '@/features/auth/LoginPage';
import SignupPage from '@/features/auth/SignupPage';
import NotebookListPage from '@/features/notebook/NotebookListPage';
import ConferencePage from '@/features/conference/ConferencePage';
import ReportPage from '@/features/report/ReportPage';
import OrganizationPage from '@/common/components/OrganizationPage';
import { Toaster } from '@/common/components/ui/toaster';

function AppRoutes() {
  // Let individual pages handle their own authentication checks
  // This prevents unnecessary API calls on app startup

  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/dataset" element={<DatasetPage />} />
      <Route path="/deepdive" element={<NotebookListPage />} />
      <Route path="/deepdive/:notebookId" element={<DeepdivePage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/conference" element={<ConferencePage />} />
      <Route path="/report" element={<ReportPage />} />
      <Route path="/organization" element={<OrganizationPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
    </Routes>
  );
}

function App() {
  return (
    <Provider store={store}>
      <AppRoutes />
      <Toaster />
    </Provider>
  );
}

export default App;