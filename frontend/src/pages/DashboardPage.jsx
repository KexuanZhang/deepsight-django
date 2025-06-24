// src/pages/DashboardPage.jsx
import React, { useState, useEffect } from "react";
import { Tab } from "@headlessui/react";
import { fetchJson } from "../lib/utils"; // simple fetch wrapper
import ReportCard from "../components/ReportCard";
import ConferenceCard from "../components/ConferenceCard";
import OrganizationCard from "../components/OrganizationCard";
import { config } from "../config";

export default function DashboardPage() {
  const tabs = ["Report", "Conference", "Organization"];
  const [selectedIndex, setSelectedIndex] = useState(0);

  const [reports, setReports] = useState([]);
  const [confsOverview, setConfsOverview] = useState(null);
  const [orgsOverview, setOrgsOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      try {
        // 1️⃣ Trending reports (admin‐selected)
        const rpt = await fetchJson(`${config.API_BASE_URL}/reports/trending`);
        setReports(rpt);

        // 2️⃣ Conferences overview
        const confOv = await fetchJson(`${config.API_BASE_URL}/conferences/overview`);
        setConfsOverview(confOv);

        // 3️⃣ Organizations overview
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span className="text-gray-500">Loading dashboard…</span>
      </div>
    );
  }

  return (
    <div className="p-8 bg-white min-h-screen">
      <h1 className="text-4xl font-bold mb-4">DeepSight</h1>
      <Tab.Group selectedIndex={selectedIndex} onChange={setSelectedIndex}>
        <Tab.List className="flex space-x-4 border-b mb-6">
          {tabs.map((tab) => (
            <Tab
              key={tab}
              className={({ selected }) =>
                `px-4 py-2 text-lg ${
                  selected
                    ? "border-b-2 border-red-600 font-semibold"
                    : "text-gray-600 hover:text-gray-900"
                }`
              }
            >
              {tab}
            </Tab>
          ))}
        </Tab.List>

        <Tab.Panels>
          {/* ─── Report Tab ──────────────────────────────────────────── */}
          <Tab.Panel>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {reports.map((r) => (
                <ReportCard key={r.report_id} report={r} />
              ))}
            </div>
          </Tab.Panel>

          {/* ─── Conference Tab ─────────────────────────────────────── */}
          <Tab.Panel>
            {/* Overview metrics */}
            {confsOverview && (
              <div className="flex justify-around text-center mb-8">
                <div>
                  <p className="text-2xl font-bold">{confsOverview.total_conferences}</p>
                  <p className="text-gray-500">Total Conferences</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{confsOverview.total_papers}</p>
                  <p className="text-gray-500">Total Papers</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{confsOverview.years_covered}</p>
                  <p className="text-gray-500">Years Covered</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{confsOverview.avg_papers_per_year}</p>
                  <p className="text-gray-500">Avg Papers/Year</p>
                </div>
              </div>
            )}
            {/* Conference list */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {confsOverview?.conferences.map((c) => (
                <ConferenceCard key={c.id} conference={c} />
              ))}
            </div>
          </Tab.Panel>

          {/* ─── Organization Tab ──────────────────────────────────── */}
          <Tab.Panel>
            {orgsOverview ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {orgsOverview.organizations.map((o) => (
                  <OrganizationCard key={o.org_id} organization={o} />
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No data available.</p>
            )}
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
}
