// src/pages/NotebookListPage.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Menu, X, ChevronDown, Grid, List } from "lucide-react";

export default function NotebookListPage() {
  const navigate = useNavigate();

  // Slide-out menu state
  const [menuOpen, setMenuOpen] = useState(false);

  // Notebook list state
  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");

  // Create form state
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  // View / sort toggles
  const [isGridView, setIsGridView] = useState(true);
  const [sortOrder, setSortOrder]   = useState("recent");

  const token = localStorage.getItem("token");

  useEffect(() => {
    async function loadNotebooks() {
      setLoading(true);
      setError("");
      if (!token) return navigate("/login");

      try {
        const res = await fetch("http://localhost:8000/api/notebooks/", {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.status === 401) return navigate("/login");
        if (!res.ok) throw new Error("Failed to load notebooks");

        const data = await res.json();
        data.sort((a, b) => {
          const aT = new Date(a.created_at).getTime();
          const bT = new Date(b.created_at).getTime();
          return sortOrder === "recent" ? bT - aT : aT - bT;
        });
        setNotebooks(data);
      } catch (e) {
        console.error(e);
        setError("Could not load your notebooks.");
      } finally {
        setLoading(false);
      }
    }
    loadNotebooks();
  }, [sortOrder, token, navigate]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await fetch("http://localhost:8000/api/notebooks/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (res.status === 401) return navigate("/login");
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Could not create notebook");
      }
      const created = await res.json();
      navigate(`/deepdive/${created.notebook_id}`);
    } catch (e) {
      console.error(e);
      setError(e.message);
    } finally {
      setCreating(false);
      setNewName("");
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col relative">
      {/* Slide-out Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 flex">
          <div className="w-64 bg-white shadow-xl p-6 z-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold">Menu</h2>
              <button onClick={() => setMenuOpen(false)}>
                <X className="h-5 w-5 text-gray-600 hover:text-gray-900"/>
              </button>
            </div>
            <nav className="space-y-4">
              <Link to="/"        className="block text-gray-700 hover:text-red-600">Home</Link>
              <Link to="/dashboard" className="block text-gray-700 hover:text-red-600">Dashboard</Link>
              <Link to="/dataset"   className="block text-gray-700 hover:text-red-600">Dataset</Link>
              <Link to="/deepdive"  className="block text-red-600 font-semibold bg-gray-100 p-2 rounded">Notebooks</Link>
            </nav>
          </div>
          <div
            className="flex-1 bg-black bg-opacity-30"
            onClick={() => setMenuOpen(false)}
          />
        </div>
      )}

      {/* Header */}
      <header className="border-b border-gray-200 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="h-6 w-6 text-gray-700"/>
          </button>
          <h1 className="text-2xl font-semibold text-gray-800">Notebooks</h1>
        </div>

        {/* Settings or other right-side icons could go here */}
        <button
          onClick={() => navigate("/settings")}
          className="text-gray-600 hover:text-gray-900"
          title="Settings"
        >
          <X className="h-6 w-6 rotate-45" /> {/* Or use a Cog icon */}
        </button>
      </header>

      {/* Main Content */}
      <main className="p-6 flex-1 overflow-auto">
        {/* Create + View/Sort Controls */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 space-y-4 md:space-y-0">
          <form onSubmit={handleCreate} className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="New notebook name…"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              disabled={creating}
            />
            <button
              type="submit"
              className={`px-4 py-2 rounded-md text-white ${
                creating ? "bg-gray-400" : "bg-red-600 hover:bg-red-700"
              }`}
              disabled={creating}
            >
              {creating ? "Creating…" : "Create"}
            </button>
          </form>

          <div className="flex items-center space-x-4">
            <button
              onClick={() => setIsGridView(true)}
              className={`p-2 rounded-md ${
                isGridView
                  ? "bg-red-100 text-red-600"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              <Grid className="h-5 w-5"/>
            </button>
            <button
              onClick={() => setIsGridView(false)}
              className={`p-2 rounded-md ${
                !isGridView
                  ? "bg-red-100 text-red-600"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              <List className="h-5 w-5"/>
            </button>
            <div className="relative">
              <select
                value={sortOrder}
                onChange={e => setSortOrder(e.target.value)}
                className="appearance-none px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
              >
                <option value="recent">Most recent</option>
                <option value="oldest">Oldest first</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 h-4 w-4 pointer-events-none"/>
            </div>
          </div>
        </div>

        {error && <p className="text-red-500 mb-4">{error}</p>}

        {loading ? (
          <p className="text-gray-500">Loading notebooks…</p>
        ) : notebooks.length === 0 ? (
          <p className="text-gray-500">You haven’t created any notebooks yet.</p>
        ) : isGridView ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {notebooks.map(nb => (
              <div
                key={nb.notebook_id}
                onClick={() => navigate(`/deepdive/${nb.notebook_id}`)}
                className="cursor-pointer bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition p-4 flex flex-col justify-between"
              >
                {/* …your card content */}
                <p className="font-semibold text-lg text-gray-800">{nb.name}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {notebooks.map(nb => (
              <div
                key={nb.notebook_id}
                onClick={() => navigate(`/deepdive/${nb.notebook_id}`)}
                className="cursor-pointer flex items-center bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition p-4"
              >
                <p className="flex-1 font-semibold text-gray-800">{nb.name}</p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
