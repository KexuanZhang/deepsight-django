import { createLazyRoute } from "@/shared/utils/lazyLoading"

// Lazy loaded route components using the enhanced lazy loading utility
export const HomePage = createLazyRoute(
  () => import("@/shared/components/common/HomePage"),
  'Home'
);

export const DatasetPage = createLazyRoute(
  () => import("@/shared/components/common/DatasetPage"),
  'Dataset'
);

export const NotebookListPage = createLazyRoute(
  () => import("@/features/notebook/pages/NotebookListPage"),
  'Notebooks'
);

export const DeepdivePage = createLazyRoute(
  () => import("@/features/notebook/pages/DeepdivePage"),
  'Notebook'
);

export const DashboardPage = createLazyRoute(
  () => import("@/features/dashboard/pages/DashboardPage"),
  'Dashboard'
);

export const ConferencePage = createLazyRoute(
  () => import("@/features/conference/pages/ConferencePage"),
  'Conference'
);

export const ReportPage = createLazyRoute(
  () => import("@/features/report/pages/ReportPage"),
  'Reports'
);

export const PodcastPage = createLazyRoute(
  () => import("@/features/podcast/pages/PodcastPage"),
  'Podcasts'
);

export const OrganizationPage = createLazyRoute(
  () => import("@/shared/components/common/OrganizationPage"),
  'Organization'
);

export const LoginPage = createLazyRoute(
  () => import("@/features/auth/pages/LoginPage"),
  'Login'
);

export const SignupPage = createLazyRoute(
  () => import("@/features/auth/pages/SignupPage"),
  'Signup'
);

// Export all lazy routes for preloading
export const lazyRoutes = [
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
];

// Preload critical routes
export const preloadCriticalRoutes = () => {
  // Preload home, dashboard, and notebook routes as they are most commonly used
  return Promise.all([
    HomePage.preload(),
    DashboardPage.preload(),
    NotebookListPage.preload(),
  ]);
};