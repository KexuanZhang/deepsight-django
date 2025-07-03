import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from './store';
import HomePage from '@/common/components/HomePage';
import DatasetPage from '@/common/components/DatasetPage';
import DeepdivePage from '@/features/notebook/DeepdivePage';
import DashboardPage from '@/features/dashboard/DashboardPage';
import LoginPage from '@/features/auth/LoginPage';
import SignupPage from '@/features/auth/SignupPage';
import NotebookListPage from '@/features/notebook/NotebookListPage';

function App() {
  return (
    <Provider store={store}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dataset" element={<DatasetPage />} />
        <Route path="/deepdive" element={<NotebookListPage />} />
        <Route path="/deepdive/:notebookId" element={<DeepdivePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Routes>
    </Provider>
  );
}

export default App;