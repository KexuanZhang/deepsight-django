import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import { checkCurrentUser } from "../auth/authSlice";
import { 
  Menu, 
  X, 
  ChevronDown, 
  Grid, 
  List, 
  LogOut, 
  Plus,
  BookOpen,
  Calendar,
  Search,
  Filter,
  MoreVertical,
  Edit3,
  Trash2
} from "lucide-react";
import { config } from "../../config";

// helper to read CSRF token from cookies
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export default function NotebookListPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isAuthenticated, user, isLoading } = useSelector((state) => state.auth);

  // UI / data state
  const [menuOpen, setMenuOpen] = useState(false);
  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [isGridView, setIsGridView] = useState(true);
  const [sortOrder, setSortOrder] = useState("recent");
  const [searchTerm, setSearchTerm] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Check authentication state on component mount
  useEffect(() => {
    const checkAuth = async () => {
      // If we already have a user (from login), skip the API check
      if (user) {
        setAuthChecked(true);
        return;
      }
      
      // Only check current user if we don't already have authentication state
      await dispatch(checkCurrentUser());
      setAuthChecked(true);
    };
    checkAuth();
  }, [dispatch, user]);

  // Redirect to login if not authenticated (after auth check is complete)
  useEffect(() => {
    if (authChecked && !isAuthenticated) {
      navigate("/login");
      return;
    }
    
    // Prime CSRF for authenticated users
    if (authChecked && isAuthenticated) {
      fetch(`${config.API_BASE_URL}/users/csrf/`, { credentials: "include" }).catch(() => {});
    }
  }, [isAuthenticated, authChecked, navigate]);

  // 2) load the list of notebooks for authenticated user
  useEffect(() => {
    if (!authChecked || !isAuthenticated || !user) return;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${config.API_BASE_URL}/notebooks/`, { credentials: "include" });
        if (res.status === 401) return navigate("/login");
        if (!res.ok) throw new Error();
        let data = await res.json();
        data.sort((a, b) => {
          const aT = new Date(a.created_at).getTime();
          const bT = new Date(b.created_at).getTime();
          return sortOrder === "recent" ? bT - aT : aT - bT;
        });
        setNotebooks(data);
      } catch {
        setError("Unable to load notebooks.");
      } finally {
        setLoading(false);
      }
    })();
  }, [authChecked, isAuthenticated, user, sortOrder, navigate]);

  // 3) create a new notebook, including user
  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim() || !user) return;
    setCreating(true);
    setError("");
    try {
      const res = await fetch(`${config.API_BASE_URL}/notebooks/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          user: user.id,
          name: newName.trim(),
          description: newDescription.trim(),
        }),
      });
      if (res.status === 401) return navigate("/login");
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || "Create failed");
      }
      const { id } = await res.json();
      navigate(`/deepdive/${id}`);
    } catch (e) {
      console.error(e);
      setError(e.message);
    } finally {
      setCreating(false);
      setNewName("");
      setNewDescription("");
      setShowCreateForm(false);
    }
  };

  // Filter notebooks based on search term
  const filteredNotebooks = notebooks.filter(notebook =>
    notebook.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (notebook.description && notebook.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  // Show loading screen while checking authentication
  if (!authChecked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Slide-out Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="w-80 bg-white shadow-2xl">
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-800">Navigation</h2>
                <button 
                  onClick={() => setMenuOpen(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-600" />
                </button>
              </div>
            </div>
            <nav className="p-6 space-y-3">
              <Link 
                to="/" 
                className="flex items-center space-x-3 px-4 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                <span>Home</span>
              </Link>
              <Link 
                to="/dashboard" 
                className="flex items-center space-x-3 px-4 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span>Dashboard</span>
              </Link>
              <Link 
                to="/dataset" 
                className="flex items-center space-x-3 px-4 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors"
              >
                <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                <span>Dataset</span>
              </Link>
              <Link 
                to="/deepdive" 
                className="flex items-center space-x-3 px-4 py-3 rounded-lg bg-red-50 text-red-600 font-medium"
              >
                <div className="w-2 h-2 rounded-full bg-red-500"></div>
                <span>Notebooks</span>
              </Link>
            </nav>
          </div>
          <div 
            className="flex-1 bg-black bg-opacity-30 backdrop-blur-sm" 
            onClick={() => setMenuOpen(false)} 
          />
        </div>
      )}

      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200/60 sticky top-0 z-40">
        <div className="w-full px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center space-x-4">
              <button 
                onClick={() => setMenuOpen(true)} 
                className="p-3 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Menu className="w-7 h-7 text-gray-700" />
              </button>
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">DeepDive</h1>
                  <p className="text-sm text-gray-500">Manage your research</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={async () => {
                  await fetch(`${config.API_BASE_URL}/users/logout/`, {
                    method: "POST",
                    credentials: "include",
                    headers: { "X-CSRFToken": getCookie("csrftoken") },
                  });
                  navigate("/login");
                }}
                className="p-3 rounded-lg hover:bg-gray-100 transition-colors"
                title="Log out"
              >
                <LogOut className="w-6 h-6 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full px-4 sm:px-6 lg:px-8 py-8">
        {/* Top Section with Search and Actions */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0 mb-6">
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search notebooks..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-white border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                />
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowCreateForm(!showCreateForm)}
                className="flex items-center space-x-2 px-4 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 transition-all shadow-lg hover:shadow-xl"
              >
                <Plus className="w-4 h-4" />
                <span className="font-medium">New Notebook</span>
              </button>
              
              <div className="flex items-center space-x-1 bg-white rounded-xl border border-gray-300 p-1">
                <button
                  onClick={() => setIsGridView(true)}
                  className={`p-2 rounded-lg transition-colors ${
                    isGridView 
                      ? "bg-red-100 text-red-600" 
                      : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsGridView(false)}
                  className={`p-2 rounded-lg transition-colors ${
                    !isGridView 
                      ? "bg-red-100 text-red-600" 
                      : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
              
              <div className="relative">
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value)}
                  className="appearance-none bg-white border border-gray-300 rounded-xl px-4 py-3 pr-10 focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest First</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Create Form */}
          {showCreateForm && (
            <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-lg mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Create New Notebook</h3>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Notebook Name *
                    </label>
                    <input
                      type="text"
                      placeholder="Enter notebook name"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      disabled={creating}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <input
                      type="text"
                      placeholder="Brief description (optional)"
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      disabled={creating}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <button
                    type="submit"
                    disabled={creating || !newName.trim()}
                    className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 disabled:from-gray-400 disabled:to-gray-500 transition-all font-medium"
                  >
                    {creating ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Creating...</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        <span>Create Notebook</span>
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCreateForm(false);
                      setNewName("");
                      setNewDescription("");
                    }}
                    className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-red-600 font-medium">{error}</p>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-red-200 border-t-red-600 rounded-full animate-spin mb-4"></div>
            <p className="text-gray-600 font-medium">Loading your notebooks...</p>
          </div>
        ) : filteredNotebooks.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-red-100 to-red-200 rounded-2xl flex items-center justify-center">
              <BookOpen className="w-10 h-10 text-red-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              {searchTerm ? "No notebooks found" : "No notebooks yet"}
            </h2>
            <p className="text-gray-600 mb-8 max-w-md mx-auto">
              {searchTerm 
                ? `No notebooks match "${searchTerm}". Try a different search term.`
                : "Create your first notebook to start organizing your research and ideas."
              }
            </p>
            {!searchTerm && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="inline-flex items-center space-x-2 px-8 py-4 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-xl hover:from-red-600 hover:to-red-700 transition-all shadow-lg hover:shadow-xl font-medium"
              >
                <Plus className="w-5 h-5" />
                <span>Create Your First Notebook</span>
              </button>
            )}
          </div>
        ) : isGridView ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredNotebooks.map((notebook) => (
              <div
                key={notebook.id}
                onClick={() => navigate(`/deepdive/${notebook.id}`)}
                className="group bg-white rounded-2xl border border-gray-200 hover:border-red-300 p-6 cursor-pointer transition-all duration-200 hover:shadow-xl hover:-translate-y-1"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                    <BookOpen className="w-5 h-5 text-white" />
                  </div>
                  <button className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-gray-100 transition-all">
                    <MoreVertical className="w-4 h-4 text-gray-400" />
                  </button>
                </div>
                
                <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-red-600 transition-colors">
                  {notebook.name}
                </h3>
                
                {notebook.description && (
                  <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                    {notebook.description}
                  </p>
                )}
                
                <div className="flex items-center text-xs text-gray-500 space-x-4">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3 h-3" />
                    <span>{formatDate(notebook.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
            <div className="divide-y divide-gray-100">
              {filteredNotebooks.map((notebook) => (
                <div
                  key={notebook.id}
                  onClick={() => navigate(`/deepdive/${notebook.id}`)}
                  className="group p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 flex-1">
                      <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform">
                        <BookOpen className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-red-600 transition-colors">
                          {notebook.name}
                        </h3>
                        {notebook.description && (
                          <p className="text-gray-600 text-sm mt-1 truncate">
                            {notebook.description}
                          </p>
                        )}
                        <div className="flex items-center text-xs text-gray-500 mt-2 space-x-4">
                          <div className="flex items-center space-x-1">
                            <Calendar className="w-3 h-3" />
                            <span>Created {formatDate(notebook.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button className="opacity-0 group-hover:opacity-100 p-2 rounded-lg hover:bg-gray-200 transition-all">
                        <Edit3 className="w-4 h-4 text-gray-400" />
                      </button>
                      <ChevronDown className="w-5 h-5 text-gray-400 rotate-90 group-hover:text-red-500 transition-colors" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
