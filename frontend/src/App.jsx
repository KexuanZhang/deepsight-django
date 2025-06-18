import React from "react";
import { Routes, Route } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import DatasetPage from "@/pages/DatasetPage";
import DeepdivePage from "@/pages/DeepdivePage";
import DashboardPage from "./pages/DashboardPage";

function App() {
  return (
    <Routes>
      {/* <Route path="/" element={<HomePage />} /> */}
      <Route path="/dataset" element={<DatasetPage />} />
      <Route path="/deepdive" element={<DeepdivePage />} />
      <Route path="/" element={<DashboardPage />} />
    </Routes>
  );
}

export default App;
