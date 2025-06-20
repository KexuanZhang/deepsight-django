import React from "react";
import { Routes, Route } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import DatasetPage from "@/pages/DatasetPage";
import DeepdivePage from "@/pages/DeepdivePage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import NotebookListPage from "./pages/NotebookListPage";


function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/dataset" element={<DatasetPage />} />
      <Route path="/deepdive" element={<NotebookListPage />} />
      <Route path="/deepdive/:notebookId" element={<DeepdivePage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
    </Routes>
  );
}

export default App;
