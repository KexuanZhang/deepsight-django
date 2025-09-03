import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { store } from '@/app/store';
import { Toaster } from "@/shared/components/ui/toaster";
import { ErrorBoundary } from "@/shared/components/ui/ErrorBoundary";
import { QueryProvider } from "@/shared/providers/QueryProvider";
import { PerformanceMonitor, reportWebVitals } from "@/shared/utils/performance";
import {
  HomePage,
  DatasetPage,
  NotebookListPage,
  DeepdivePage,
  DashboardPage,
  ConferencePage,
  ReportPage,
  PodcastPage,
  OrganizationPage,
  LoginPage,
  SignupPage,
  preloadCriticalRoutes,
} from "@/features/routes/LazyRoutes";

function AppRoutes() {
  // Preload critical routes on mount
  useEffect(() => {
    preloadCriticalRoutes().catch(console.warn);
  }, []);

  return (
    <Routes>
      <Route path="/" element={<HomePage.Component />} />
      <Route path="/dataset" element={<DatasetPage.Component />} />
      <Route path="/deepdive" element={<NotebookListPage.Component />} />
      <Route path="/deepdive/:notebookId" element={<DeepdivePage.Component />} />
      <Route path="/dashboard" element={<DashboardPage.Component />} />
      <Route path="/conference" element={<ConferencePage.Component />} />
      <Route path="/report" element={<ReportPage.Component />} />
      <Route path="/podcast" element={<PodcastPage.Component />} />
      <Route path="/organization" element={<OrganizationPage.Component />} />
      <Route path="/login" element={<LoginPage.Component />} />
      <Route path="/signup" element={<SignupPage.Component />} />
    </Routes>
  );
}

function App() {
  useEffect(() => {
    // Initialize performance monitoring
    const monitor = PerformanceMonitor.getInstance();
    monitor.startMonitoring('navigation');
    monitor.startMonitoring('paint');
    monitor.startMonitoring('resource');

    // Report Web Vitals
    reportWebVitals((metric) => {
      console.log('Web Vital:', metric);
    });

    return () => {
      monitor.disconnect();
    };
  }, []);

  return (
    <Provider store={store}>
      <QueryProvider>
        <ErrorBoundary level="page">
          <AppRoutes />
          <Toaster />
        </ErrorBoundary>
      </QueryProvider>
    </Provider>
  );
}

export default App;