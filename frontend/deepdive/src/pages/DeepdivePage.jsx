// // src/pages/DeepdivePage.jsx
// import React, { useState, useEffect } from "react";
// import { motion } from "framer-motion";
// import { Toaster } from "@/components/ui/toaster";
// import { Menu, X, ArrowLeft } from "lucide-react";
// import Logo from "@/components/Logo";
// import SourcesList from "@/components/SourcesList";
// import ChatPanel from "@/components/ChatPanel";
// import StudioPanel from "@/components/StudioPanel";
// import Footer from "@/components/Footer";
// import "highlight.js/styles/github.css";
// import { Link, useParams, useNavigate } from "react-router-dom";

// export default function DeepdivePage() {
//   const { notebookId } = useParams();
//   const navigate = useNavigate();

//   const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
//   const [menuOpen, setMenuOpen] = useState(false);

//   // Notebook metadata state
//   const [notebookMeta, setNotebookMeta] = useState(null);
//   const [loadingNotebook, setLoadingNotebook] = useState(true);
//   const [loadError, setLoadError] = useState("");

//   // JWT token from localStorage
//   const token = localStorage.getItem("token");

//   useEffect(() => {
//     async function fetchMeta() {
//       setLoadingNotebook(true);
//       setLoadError("");

//       if (!token) {
//         navigate("/login");
//         return;
//       }

//       try {
//         const res = await fetch(
//           `http://localhost:8000/api/notebooks/${notebookId}`,
//           {
//             headers: {
//               "Content-Type": "application/json",
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );

//         if (res.status === 401) {
//           navigate("/login");
//           return;
//         }
//         if (res.status === 404) {
//           setLoadError("Notebook not found.");
//           return;
//         }
//         if (!res.ok) {
//           throw new Error("Failed to load notebook data.");
//         }

//         const data = await res.json();
//         setNotebookMeta(data);
//       } catch (e) {
//         console.error(e);
//         setLoadError("Could not load notebook data.");
//       } finally {
//         setLoadingNotebook(false);
//       }
//     }

//     fetchMeta();
//   }, [notebookId, token, navigate]);

//   if (loadingNotebook) {
//     return (
//       <div className="flex items-center justify-center h-screen bg-white">
//         <span className="text-gray-500">Loading notebook…</span>
//       </div>
//     );
//   }

//   if (loadError) {
//     return (
//       <div className="flex flex-col items-center justify-center h-screen bg-white p-4">
//         <p className="text-red-600 mb-4">{loadError}</p>
//         <button
//           onClick={() => navigate("/deepdive")}
//           className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
//         >
//           Back to Notebooks
//         </button>
//       </div>
//     );
//   }

//   return (
//     <div className="min-h-screen bg-white flex flex-col relative">
//       {/* Sidebar Menu */}
//       {menuOpen && (
//         <div className="fixed inset-0 z-50 flex">
//           <div className="w-64 bg-white shadow-xl p-6 z-50">
//             <div className="flex justify-between items-center mb-6">
//               <h2 className="text-lg font-semibold">Menu</h2>
//               <button
//                 onClick={() => setMenuOpen(false)}
//                 className="text-gray-600 hover:text-gray-900"
//               >
//                 <X className="h-5 w-5" />
//               </button>
//             </div>
//             <nav className="space-y-4">
//               <Link to="/" className="block text-gray-700 hover:text-red-600">
//                 Home Page
//               </Link>
//               <Link
//                 to="/dashboard"
//                 className="block text-gray-700 hover:text-red-600"
//               >
//                 Dashboard
//               </Link>
//               <Link
//                 to="/dataset"
//                 className="block text-gray-700 hover:text-red-600"
//               >
//                 Dataset
//               </Link>
//               <Link
//                 to="/deepdive"
//                 className="block text-red-600 font-semibold bg-gray-100 p-2 rounded"
//               >
//                 Notebooks
//               </Link>
//             </nav>
//           </div>
//           <div
//             className="flex-1 bg-black bg-opacity-30"
//             onClick={() => setMenuOpen(false)}
//           />
//         </div>
//       )}

//       {/* Header */}
//       <header className="border-b border-gray-200 p-4 flex justify-between items-center relative z-10">
//         <div className="flex items-center space-x-4">
//           {/* Back Button */}
//           <button
//             onClick={() => navigate("/deepdive")}
//             className="p-2 rounded-md hover:bg-gray-100"
//             title="Back to Notebooks"
//           >
//             <ArrowLeft className="h-6 w-6 text-gray-700" />
//           </button>

//           {/* Menu Toggle */}
//           <button
//             onClick={() => setMenuOpen(true)}
//             className="p-2 rounded-md hover:bg-gray-100"
//           >
//             <Menu className="h-6 w-6 text-gray-700" />
//           </button>

//           {/* Logo & Title */}
//           <Logo />
//           {notebookMeta && (
//             <h2 className="text-xl font-semibold ml-4">
//               {notebookMeta.name}
//             </h2>
//           )}
//         </div>

//         {/* Language Switcher */}
//         <div className="relative group">
//           <div className="cursor-pointer text-gray-600 text-lg flex items-center">
//             <span className="text-2xl">文A</span>
//           </div>
//           <div className="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
//             <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
//               🇺🇸 <span className="ml-2">English</span>
//             </button>
//             <button className="w-full flex items-center px-3 py-2 text-sm hover:bg-gray-100">
//               🇨🇳 <span className="ml-2">简体中文</span>
//             </button>
//           </div>
//         </div>
//       </header>

//       {/* Main Content */}
//       <main className="flex flex-col flex-1 relative">
//         <div className="flex-1">
//           <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 h-[calc(100vh-4rem)] overflow-hidden relative">
//             {/* Sources Panel */}
//             {!isSourcesCollapsed && (
//               <motion.div
//                 initial={{ opacity: 0, x: -10 }}
//                 animate={{ opacity: 1, x: 0 }}
//                 transition={{ duration: 0.3 }}
//                 className="col-span-1 md:col-span-3 border border-gray-200 rounded-lg overflow-auto relative"
//               >
//                 <SourcesList notebookId={notebookId} />
//                 <button
//                   onClick={() => setIsSourcesCollapsed(true)}
//                   className="absolute right-[-10px] top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded shadow w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 z-50"
//                   title="Collapse Sources"
//                 >
//                   ❮
//                 </button>
//               </motion.div>
//             )}

//             {/* Expand Sources Button */}
//             {isSourcesCollapsed && (
//               <button
//                 onClick={() => setIsSourcesCollapsed(false)}
//                 className="absolute left-0 top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded shadow w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 z-50"
//                 title="Expand Sources"
//               >
//                 ❯
//               </button>
//             )}

//             {/* Chat Panel */}
//             <motion.div
//               initial={{ opacity: 0, y: 20 }}
//               animate={{ opacity: 1, y: 0 }}
//               transition={{ duration: 0.3, delay: 0.1 }}
//               className={`border border-gray-200 rounded-lg overflow-auto ${
//                 isSourcesCollapsed
//                   ? "col-span-1 md:col-span-6"
//                   : "col-span-1 md:col-span-5"
//               }`}
//             >
//               <ChatPanel notebookId={notebookId} />
//             </motion.div>

//             {/* Studio Panel */}
//             <motion.div
//               initial={{ opacity: 0, x: 20 }}
//               animate={{ opacity: 1, x: 0 }}
//               transition={{ duration: 0.3, delay: 0.2 }}
//               className={`border border-gray-200 rounded-lg overflow-auto ${
//                 isSourcesCollapsed
//                   ? "col-span-1 md:col-span-6"
//                   : "col-span-1 md:col-span-4"
//               }`}
//             >
//               <StudioPanel notebookId={notebookId} />
//             </motion.div>
//           </div>
//         </div>
//       </main>

//       {/* Footer */}
//       <Footer />
//       <Toaster />
//     </div>
//   );
// }

// src/pages/DeepdivePage.jsx
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Toaster } from "@/components/ui/toaster";
import { Menu, X, ArrowLeft, LogOut } from "lucide-react";
import Logo from "@/components/Logo";
import SourcesList from "@/components/SourcesList";
import ChatPanel from "@/components/ChatPanel";
import StudioPanel from "@/components/StudioPanel";
import Footer from "@/components/Footer";
import "highlight.js/styles/github.css";
import { Link, useParams, useNavigate } from "react-router-dom";

// helper to read CSRF token from cookies
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export default function DeepdivePage() {
  const { notebookId } = useParams();
  const navigate       = useNavigate();

  const [isSourcesCollapsed, setIsSourcesCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const [notebookMeta, setNotebookMeta] = useState(null);
  const [loadingNotebook, setLoadingNotebook] = useState(true);
  const [loadError, setLoadError] = useState("");

  // prime CSRF on mount
  useEffect(() => {
    fetch("/api/users/csrf/", {
      method: "GET",
      credentials: "include",
    }).catch(() => {});
  }, []);

  // fetch notebook metadata
  useEffect(() => {
    async function fetchMeta() {
      setLoadingNotebook(true);
      setLoadError("");

      try {
        const res = await fetch(`/api/notebooks/${notebookId}/`, {
          credentials: "include",
        });

        if (res.status === 401) {
          navigate("/login");
          return;
        }
        if (res.status === 404) {
          setLoadError("Notebook not found.");
          return;
        }
        if (!res.ok) {
          throw new Error("Failed to load notebook data.");
        }

        const data = await res.json();
        setNotebookMeta(data);
      } catch (e) {
        console.error(e);
        setLoadError("Could not load notebook data.");
      } finally {
        setLoadingNotebook(false);
      }
    }

    fetchMeta();
  }, [notebookId, navigate]);

  if (loadingNotebook) {
    return (
      <div className="flex items-center justify-center h-screen bg-white">
        <span className="text-gray-500">Loading notebook…</span>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-white p-4">
        <p className="text-red-600 mb-4">{loadError}</p>
        <button
          onClick={() => navigate("/deepdive")}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Back to Notebooks
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white flex flex-col relative">
      {/* Sidebar Menu */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div className="w-64 bg-white shadow-xl p-6 z-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold">Menu</h2>
              <button onClick={() => setMenuOpen(false)}>
                <X className="h-5 w-5 text-gray-600 hover:text-gray-900" />
              </button>
            </div>
            <nav className="space-y-4">
              <Link to="/"        className="block text-gray-700 hover:text-red-600">Home Page</Link>
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
      <header className="border-b border-gray-200 p-4 flex justify-between items-center relative z-10">
        <div className="flex items-center space-x-4">
          {/* Back Button */}
          <button
            onClick={() => navigate("/deepdive")}
            className="p-2 rounded-md hover:bg-gray-100"
            title="Back to Notebooks"
          >
            <ArrowLeft className="h-6 w-6 text-gray-700" />
          </button>

          {/* Menu Toggle */}
          <button
            onClick={() => setMenuOpen(true)}
            className="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu className="h-6 w-6 text-gray-700" />
          </button>

          {/* Logo & Title */}
          <Logo />
          <h2 className="text-xl font-semibold ml-4">
            {notebookMeta.name}
          </h2>
        </div>

        {/* Logout */}
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
            className="text-gray-600 hover:text-gray-900"
            title="Logout"
          >
            <LogOut className="h-6 w-6" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-col flex-1 relative">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 h-[calc(100vh-4rem)] overflow-hidden relative">
          {/* Sources Panel */}
          {!isSourcesCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="col-span-1 md:col-span-3 border border-gray-200 rounded-lg overflow-auto relative"
            >
              <SourcesList notebookId={notebookId} />
              <button
                onClick={() => setIsSourcesCollapsed(true)}
                className="absolute right-[-10px] top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded shadow w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 z-50"
                title="Collapse Sources"
              >
                ❮
              </button>
            </motion.div>
          )}

          {/* Expand Sources Button */}
          {isSourcesCollapsed && (
            <button
              onClick={() => setIsSourcesCollapsed(false)}
              className="absolute left-0 top-1/2 transform -translate-y-1/2 bg-white border border-gray-200 rounded shadow w-7 h-7 flex items-center justify-center text-gray-400 hover:text-gray-600 z-50"
              title="Expand Sources"
            >
              ❯
            </button>
          )}

          {/* Chat Panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className={`border border-gray-200 rounded-lg overflow-auto ${
              isSourcesCollapsed ? "col-span-1 md:col-span-6" : "col-span-1 md:col-span-5"
            }`}
          >
            <ChatPanel notebookId={notebookId} />
          </motion.div>

          {/* Studio Panel */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className={`border border-gray-200 rounded-lg overflow-auto ${
              isSourcesCollapsed ? "col-span-1 md:col-span-6" : "col-span-1 md:col-span-4"
            }`}
          >
            <StudioPanel notebookId={notebookId} />
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
      <Toaster />
    </div>
  );
}
