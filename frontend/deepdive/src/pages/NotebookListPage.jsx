// import React, { useEffect, useState } from "react";
// import { useNavigate, Link } from "react-router-dom";
// import { Menu, X, ChevronDown, Grid, List, LogOut } from "lucide-react";

// // helper to read CSRF token from cookies
// function getCookie(name) {
//   const match = document.cookie.match(
//     new RegExp(`(^| )${name}=([^;]+)`)
//   );
//   return match ? decodeURIComponent(match[2]) : null;
// }

// export default function NotebookListPage() {
//   const navigate = useNavigate();

//   // Slide-out menu state
//   const [menuOpen, setMenuOpen] = useState(false);

//   // Notebook list state
//   const [notebooks, setNotebooks] = useState([]);
//   const [loading, setLoading]   = useState(true);
//   const [error, setError]       = useState("");

//   // Create form state
//   const [newName, setNewName]   = useState("");
//   const [creating, setCreating] = useState(false);

//   // View / sort toggles
//   const [isGridView, setIsGridView] = useState(true);
//   const [sortOrder, setSortOrder]   = useState("recent");

//   // Prime CSRF on mount
//   useEffect(() => {
//     fetch("/api/users/csrf/", {
//       method: "GET",
//       credentials: "include",
//     }).catch(() => {});
//   }, []);

//   // Load notebooks
//   useEffect(() => {
//     async function loadNotebooks() {
//       setLoading(true);
//       setError("");
//       try {
//         const res = await fetch("/api/notebooks/", {
//           credentials: "include",
//         });
//         if (res.status === 401) return navigate("/login");
//         if (!res.ok) throw new Error("Failed to load notebooks");

//         let data = await res.json();
//         data.sort((a, b) => {
//           const aT = new Date(a.created_at).getTime();
//           const bT = new Date(b.created_at).getTime();
//           return sortOrder === "recent" ? bT - aT : aT - bT;
//         });
//         setNotebooks(data);
//       } catch (e) {
//         console.error(e);
//         setError("Could not load your notebooks.");
//       } finally {
//         setLoading(false);
//       }
//     }
//     loadNotebooks();
//   }, [sortOrder, navigate]);

//   // Create a new notebook
//   const handleCreate = async (e) => {
//     e.preventDefault();
//     if (!newName.trim()) return;
//     setCreating(true);
//     try {
//       const res = await fetch("/api/notebooks/", {
//         method: "POST",
//         credentials: "include",
//         headers: {
//           "Content-Type": "application/json",
//           "X-CSRFToken": getCookie("csrftoken"),
//         },
//         body: JSON.stringify({ name: newName.trim() }),
//       });
//       if (res.status === 401) return navigate("/login");
//       if (!res.ok) {
//         const err = await res.json().catch(() => null);
//         throw new Error(err?.detail || "Could not create notebook");
//       }
//       const created = await res.json();
//       navigate(`/deepdive/${created.id}`);
//     } catch (e) {
//       console.error(e);
//       setError(e.message);
//     } finally {
//       setCreating(false);
//       setNewName("");
//     }
//   };

//   return (
//     <div className="min-h-screen bg-white flex flex-col relative">
//       {/* Slide-out Menu */}
//       {menuOpen && (
//         <div className="fixed inset-0 z-40 flex">
//           <div className="w-64 bg-white shadow-xl p-6 z-50">
//             <div className="flex justify-between items-center mb-6">
//               <h2 className="text-lg font-semibold">Menu</h2>
//               <button onClick={() => setMenuOpen(false)}>
//                 <X className="h-5 w-5 text-gray-600 hover:text-gray-900"/>
//               </button>
//             </div>
//             <nav className="space-y-4">
//               <Link to="/"        className="block text-gray-700 hover:text-red-600">Home</Link>
//               <Link to="/dashboard" className="block text-gray-700 hover:text-red-600">Dashboard</Link>
//               <Link to="/dataset"   className="block text-gray-700 hover:text-red-600">Dataset</Link>
//               <Link to="/deepdive"  className="block text-red-600 font-semibold bg-gray-100 p-2 rounded">Notebooks</Link>
//             </nav>
//           </div>
//           <div
//             className="flex-1 bg-black bg-opacity-30"
//             onClick={() => setMenuOpen(false)}
//           />
//         </div>
//       )}

//       {/* Header */}
//       <header className="border-b border-gray-200 px-6 py-4 flex justify-between items-center">
//         <div className="flex items-center space-x-4">
//           <button
//             onClick={() => setMenuOpen(true)}
//             className="p-2 rounded-md hover:bg-gray-100"
//           >
//             <Menu className="h-6 w-6 text-gray-700"/>
//           </button>
//           <h1 className="text-2xl font-semibold text-gray-800">Notebooks</h1>
//         </div>

//         <div className="flex items-center space-x-4">
//           <button onClick={async () => {
//               await fetch("/api/users/logout/", {
//                 method: "POST",
//                 credentials: "include",
//                 headers: { "X-CSRFToken": getCookie("csrftoken") },
//               });
//               navigate("/login");
//             }}
//             className="text-gray-600 hover:text-gray-900"
//             title="Logout"
//           >
//             <LogOut className="h-6 w-6" />
//           </button>
//           <button
//             onClick={() => navigate("/settings")}
//             className="text-gray-600 hover:text-gray-900"
//             title="Settings"
//           >
//             <X className="h-6 w-6 rotate-45" />
//           </button>
//         </div>
//       </header>

//       {/* Main Content */}
//       <main className="p-6 flex-1 overflow-auto">
//         {/* Create + View/Sort Controls */}
//         <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 space-y-4 md:space-y-0">
//           <form onSubmit={handleCreate} className="flex items-center space-x-2">
//             <input
//               type="text"
//               placeholder="New notebook name…"
//               value={newName}
//               onChange={e => setNewName(e.target.value)}
//               className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
//               disabled={creating}
//             />
//             <button
//               type="submit"
//               className={`px-4 py-2 rounded-md text-white ${
//                 creating ? "bg-gray-400" : "bg-red-600 hover:bg-red-700"
//               }`}
//               disabled={creating}
//             >
//               {creating ? "Creating…" : "Create"}
//             </button>
//           </form>

//           <div className="flex items-center space-x-4">
//             <button
//               onClick={() => setIsGridView(true)}
//               className={`p-2 rounded-md ${
//                 isGridView
//                   ? "bg-red-100 text-red-600"
//                   : "text-gray-500 hover:text-gray-800"
//               }`}
//             >
//               <Grid className="h-5 w-5"/>
//             </button>
//             <button
//               onClick={() => setIsGridView(false)}
//               className={`p-2 rounded-md ${
//                 !isGridView
//                   ? "bg-red-100 text-red-600"
//                   : "text-gray-500 hover:text-gray-800"
//               }`}
//             >
//               <List className="h-5 w-5"/>
//             </button>
//             <div className="relative">
//               <select
//                 value={sortOrder}
//                 onChange={e => setSortOrder(e.target.value)}
//                 className="appearance-none px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500"
//               >
//                 <option value="recent">Most recent</option>
//                 <option value="oldest">Oldest first</option>
//               </select>
//               <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 h-4 w-4 pointer-events-none"/>
//             </div>
//           </div>
//         </div>

//         {error && <p className="text-red-500 mb-4">{error}</p>}

//         {loading ? (
//           <p className="text-gray-500">Loading notebooks…</p>
//         ) : notebooks.length === 0 ? (
//           <p className="text-gray-500">You haven’t created any notebooks yet.</p>
//         ) : isGridView ? (
//           <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
//             {notebooks.map(nb => (
//               <div
//                 key={nb.id}
//                 onClick={() => navigate(`/deepdive/${nb.id}`)}
//                 className="cursor-pointer bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition p-4 flex flex-col justify-between"
//               >
//                 <p className="font-semibold text-lg text-gray-800">{nb.name}</p>
//               </div>
//             ))}
//           </div>
//         ) : (
//           <div className="space-y-4">
//             {notebooks.map(nb => (
//               <div
//                 key={nb.id}
//                 onClick={() => navigate(`/deepdive/${nb.id}`)}
//                 className="cursor-pointer flex items-center bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition p-4"
//               >
//                 <p className="flex-1 font-semibold text-gray-800">{nb.name}</p>
//               </div>
//             ))}
//           </div>
//         )}
//       </main>
//     </div>
//   );
// }


// src/pages/NotebookListPage.jsx
import React, { useEffect, useState } from "react";
import { useNavigate, Link }         from "react-router-dom";
import { Menu, X, ChevronDown, Grid, List, LogOut } from "lucide-react";

// helper to read CSRF token from cookies
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export default function NotebookListPage() {
  const navigate = useNavigate();

  // UI / data state
  const [menuOpen, setMenuOpen]           = useState(false);
  const [notebooks, setNotebooks]         = useState([]);
  const [loading, setLoading]             = useState(true);
  const [error, setError]                 = useState("");
  const [newName, setNewName]             = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating]           = useState(false);
  const [isGridView, setIsGridView]       = useState(true);
  const [sortOrder, setSortOrder]         = useState("recent");
  const [currentUser, setCurrentUser]     = useState(null);

  // 1) Prime CSRF & fetch current user
  useEffect(() => {
    // drop the CSRF cookie
    fetch("/api/users/csrf/", { credentials: "include" }).catch(() => {});
    // get the logged-in user
    fetch("/api/users/me/", { credentials: "include" })
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("Not authenticated");
      })
      .then(data => setCurrentUser(data))
      .catch(() => {
        setCurrentUser(null);
        navigate("/login");
      });
  }, [navigate]);

  // 2) load the list of notebooks for currentUser
  useEffect(() => {
    if (!currentUser) return;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const res = await fetch("/api/notebooks/", { credentials: "include" });
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
  }, [currentUser, sortOrder, navigate]);

  // 3) create a new notebook, including user
  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim() || !currentUser) return;
    setCreating(true);
    setError("");
    try {
      const res = await fetch("/api/notebooks/", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          user:        currentUser.id,
          name:        newName.trim(),
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
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button onClick={() => setMenuOpen(true)} className="p-2 rounded hover:bg-gray-100">
              <Menu className="w-6 h-6 text-gray-700" />
            </button>
            <h1 className="text-2xl font-bold">My Notebooks</h1>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={async () => {
                await fetch("/api/users/logout/", {
                  method: "POST",
                  credentials: "include",
                  headers: { "X-CSRFToken": getCookie("csrftoken") },
                });
                navigate("/login");
              }}
              title="Log out"
              className="p-2 rounded hover:bg-gray-100"
            >
              <LogOut className="w-6 h-6 text-gray-700" />
            </button>
            <button onClick={() => navigate("/settings")} title="Settings" className="p-2 rounded hover:bg-gray-100">
              <X className="w-6 h-6 text-gray-700 rotate-45" />
            </button>
          </div>
        </div>

        {/* Create + Controls */}
        <div className="bg-white border-t">
          <div className="max-w-5xl mx-auto px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
            <form onSubmit={handleCreate} className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input
                type="text"
                placeholder="Notebook name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                disabled={creating}
                className="px-4 py-2 border rounded focus:ring-2 focus:ring-red-500"
              />
              <input
                type="text"
                placeholder="Description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                disabled={creating}
                className="px-4 py-2 border rounded focus:ring-2 focus:ring-red-500"
              />
              <button
                type="submit"
                disabled={creating}
                className={`sm:col-span-2 px-6 py-2 rounded font-medium text-white ${
                  creating ? "bg-gray-400" : "bg-red-600 hover:bg-red-700"
                }`}
              >
                {creating ? "Creating…" : "Create Notebook"}
              </button>
            </form>

            <div className="flex items-center space-x-4">
              <button
                onClick={() => setIsGridView(true)}
                className={`p-2 rounded ${
                  isGridView ? "bg-red-100 text-red-600" : "text-gray-500 hover:text-gray-800"
                }`}
              >
                <Grid className="w-5 h-5" />
              </button>
              <button
                onClick={() => setIsGridView(false)}
                className={`p-2 rounded ${
                  !isGridView ? "bg-red-100 text-red-600" : "text-gray-500 hover:text-gray-800"
                }`}
              >
                <List className="w-5 h-5" />
              </button>
              <div className="relative">
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value)}
                  className="pl-3 pr-8 py-2 border rounded focus:ring-2 focus:ring-red-500 appearance-none"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest First</option>
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 w-4 h-4 pointer-events-none" />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Slide‐out Menu (unchanged) */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 flex">
          <div className="w-64 bg-white shadow-xl p-6 z-50">
            {/* … your menu links */}
          </div>
          <div className="flex-1 bg-black bg-opacity-30" onClick={() => setMenuOpen(false)} />
        </div>
      )}

      {/* Main */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-8">
        {error && <div className="mb-4 text-red-600">{error}</div>}

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-red-600"></div>
          </div>
        ) : notebooks.length === 0 ? (
          <div className="text-center py-20">
            <h2 className="text-xl font-semibold mb-4">No Notebooks Yet</h2>
            <p className="text-gray-600 mb-6">Create your first notebook to get started.</p>
            <button
              onClick={() => document.querySelector('input[placeholder="Notebook name"]').focus()}
              className="px-6 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Create Notebook
            </button>
          </div>
        ) : isGridView ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {notebooks.map((nb) => (
              <div
                key={nb.id}
                onClick={() => navigate(`/deepdive/${nb.id}`)}
                className="p-6 bg-white rounded-lg shadow hover:shadow-lg transition cursor-pointer"
              >
                <h3 className="text-lg font-semibold">{nb.name}</h3>
                {nb.description && <p className="mt-2 text-gray-600">{nb.description}</p>}
                <p className="mt-4 text-sm text-gray-400">
                  Created {new Date(nb.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y">
            {notebooks.map((nb) => (
              <div
                key={nb.id}
                onClick={() => navigate(`/deepdive/${nb.id}`)}
                className="py-4 flex justify-between items-center cursor-pointer hover:bg-white hover:shadow transition rounded"
              >
                <div>
                  <h3 className="font-semibold">{nb.name}</h3>
                  {nb.description && <p className="text-gray-600 text-sm">{nb.description}</p>}
                </div>
                <ChevronDown className="w-5 h-5 text-gray-400 rotate-90" />
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
