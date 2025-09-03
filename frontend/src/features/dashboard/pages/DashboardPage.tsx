// src/pages/DashboardPage.tsx
import React, { useState, useEffect } from "react";
import { fetchJson } from "@/shared/utils/utils"; // simple fetch wrapper
import ReportListItem from "@/features/report/components/ReportListItem";
import PodcastListItem from "@/features/podcast/components/PodcastListItem";
import ReportEditor from "@/features/report/components/ReportEditor";
import { config } from "@/config";

interface Report {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  content?: string;
  description?: string;
  [key: string]: any;
}

interface Podcast {
  id: string;
  title: string;
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  description?: string;
  topic?: string;
  audioUrl?: string;
  audio_file?: string;
  duration?: number;
  [key: string]: any;
}

interface Conference {
  name: string;
  location: string;
  year: string;
  summary: string;
}

interface Organization {
  name: string;
  type: string;
  description: string;
  [key: string]: any;
}

interface ConferencesOverview {
  total_conferences: number;
  total_papers: number;
  years_covered: number;
  avg_papers_per_year: number;
  conferences: Conference[];
}

interface OrganizationsOverview {
  organizations: Organization[];
}

export default function DashboardPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [confsOverview, setConfsOverview] = useState<ConferencesOverview | null>(null);
  const [orgsOverview, setOrgsOverview] = useState<OrganizationsOverview | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      try {
        // 1️⃣ Trending reports (admin‐selected)
        const rpt = await fetchJson(`${config.API_BASE_URL}/reports/trending`);
        setReports(rpt);

        // 2️⃣ Podcasts
        const pdc = await fetchJson(`${config.API_BASE_URL}/podcasts/`);
        setPodcasts(pdc);

        // 3️⃣ Conferences overview
        const confOv = await fetchJson(`${config.API_BASE_URL}/conferences/overview`);
        setConfsOverview(confOv);

        // 4️⃣ Organizations overview
        const orgOv = await fetchJson(`${config.API_BASE_URL}/organizations/overview`);
        setOrgsOverview(orgOv);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, []);

  const handleReportSelect = (report: Report) => {
    setSelectedReport(report);
  };

  const handlePodcastSelect = (podcast: Podcast) => {
    // Handle podcast selection
    console.log('Selected podcast:', podcast);
  };

  const handleViewModeChange = () => {
    // Toggle view mode
    console.log('Toggle view mode');
  };

  const handleLanguageChange = () => {
    // Toggle language
    console.log('Toggle language');
  };

  const handleBackToList = () => {
    setSelectedReport(null);
  };

  const handleDeleteReport = (report: Report) => {
    // Handle report deletion
    console.log('Deleting report:', report.id);
    setReports(reports.filter(r => r.id !== report.id));
    setSelectedReport(null);
  };

  const handleSaveReport = (report: Report, content: string) => {
    // Handle report saving
    console.log('Saving report:', report.id, content);
    // You can implement API call here to save the content
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span className="text-gray-500">Loading dashboard…</span>
      </div>
    );
  }

  // Show report editor if a report is selected
  if (selectedReport) {
    return (
      <ReportEditor
        report={selectedReport}
        onBack={handleBackToList}
        onDelete={handleDeleteReport}
        onSave={handleSaveReport}
      />
    );
  }

  return (
    <div className="p-8 bg-white min-h-screen">
      <h1 className="text-4xl font-bold mb-8">DeepSight</h1>
      
      <div className="max-w-4xl mx-auto">
        {/* Content Section */}
        <div className="flex-1">
          {/* Reports Section */}
          {reports.length > 0 && (
            <div className="mb-8">
              {reports.map((report) => (
                <ReportListItem
                  key={report.id}
                  report={report}
                  onSelect={handleReportSelect}
                />
              ))}
            </div>
          )}

          {/* Podcasts Section */}
          {podcasts.length > 0 && (
            <div>
              {podcasts.map((podcast) => (
                <PodcastListItem
                  key={podcast.id}
                  podcast={podcast}
                  onSelect={handlePodcastSelect}
                />
              ))}
            </div>
          )}

          {/* Empty State */}
          {!loading && reports.length === 0 && podcasts.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">📊</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No content yet</h3>
              <p className="text-sm text-gray-500">
                Get started by creating your first research report or podcast.
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons - Fixed on the right */}
        <div className="fixed right-8 top-1/2 transform -translate-y-1/2 flex flex-col space-y-4">
          {/* Grid View Button */}
          <button
            onClick={handleViewModeChange}
            className="w-12 h-12 bg-gray-200 rounded-lg flex items-center justify-center hover:bg-gray-300 transition-colors"
            title="Toggle view mode"
          >
            <div className="grid grid-cols-2 gap-1">
              <div className="w-2 h-2 bg-gray-600 rounded"></div>
              <div className="w-2 h-2 bg-gray-600 rounded"></div>
              <div className="w-2 h-2 bg-gray-600 rounded"></div>
              <div className="w-2 h-2 bg-gray-600 rounded"></div>
            </div>
          </button>

          {/* Language Toggle Button */}
          <button
            onClick={handleLanguageChange}
            className="w-12 h-12 bg-pink-500 rounded-full flex items-center justify-center text-white font-medium hover:bg-pink-600 transition-colors"
            title="Toggle language"
          >
            中A
          </button>
        </div>
      </div>
    </div>
  );
}
