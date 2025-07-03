// // src/pages/LoginPage.jsx
// import React, { useState } from "react";
// import { useNavigate } from "react-router-dom";

// export default function LoginPage() {
//   const navigate = useNavigate();
//   const [username, setUsername] = useState("");
//   const [password, setPassword] = useState("");
//   const [error, setError] = useState("");

//   const handleLogin = async (e) => {
//     e.preventDefault();
//     setError("");

//     try {
//       // ▶︎ Change this URL to point at your FastAPI backend
//       const response = await fetch("http://localhost:8000/login", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ username, password }),
//       });

//       // If login failed (status 4xx or 5xx), try to parse JSON error
//       if (!response.ok) {
//         let errMsg = "Login failed. Please try again.";
//         const contentType = response.headers.get("content-type") || "";
//         if (contentType.includes("application/json")) {
//           const errJson = await response.json().catch(() => null);
//           if (errJson && errJson.detail) {
//             errMsg = errJson.detail;
//           }
//         }
//         setError(errMsg);
//         return;
//       }

//       // At this point, response.ok is true. Attempt to parse JSON
//       const contentType = response.headers.get("content-type") || "";
//       let data = null;
//       if (contentType.includes("application/json")) {
//         data = await response.json().catch(() => null);
//       }

//       if (!data || !data.access_token) {
//         setError("Login succeeded but no token was returned.");
//         return;
//       }

//       // Store the JWT in localStorage, then navigate into /deepdive
//       localStorage.setItem("token", data.access_token);
//       navigate("/deepdive");
//     } catch (err) {
//       console.error(err);
//       setError("Network error. Please try again.");
//     }
//   };

//   return (
//     <div className="flex justify-center items-center h-screen bg-gray-50">
//       <form
//         onSubmit={handleLogin}
//         className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm"
//       >
//         <h2 className="text-xl font-semibold mb-4 text-center">Login</h2>
//         {error && (
//           <div className="bg-red-100 text-red-700 text-sm p-2 rounded mb-4">
//             {error}
//           </div>
//         )}
//         <input
//           type="text"
//           placeholder="Username"
//           value={username}
//           onChange={(e) => setUsername(e.target.value)}
//           className="w-full px-4 py-2 mb-3 border border-gray-300 rounded"
//           required
//         />
//         <input
//           type="password"
//           placeholder="Password"
//           value={password}
//           onChange={(e) => setPassword(e.target.value)}
//           className="w-full px-4 py-2 mb-4 border border-gray-300 rounded"
//           required
//         />
//         <button
//           type="submit"
//           className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition"
//         >
//           Log In
//         </button>
//       </form>
//     </div>
//   );
// }

// src/pages/LoginPage.jsx
// src/pages/LoginPage.jsx
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { loginUser } from "./authSlice";
import { config } from "../../config";

// helper to read CSRF token from cookies
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isLoading, error, isAuthenticated } = useSelector((state) => state.auth);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // prime CSRF cookie by hitting the CSRF endpoint
  useEffect(() => {
    fetch(`${config.API_BASE_URL}/users/csrf/`, {
      method: "GET",
      credentials: "include",
    }).catch(() => {});
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    dispatch(loginUser({ username, password }));
  };

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/deepdive");
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="flex justify-center items-center h-screen bg-gray-50">
      <form
        onSubmit={handleLogin}
        className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm"
      >
        <h2 className="text-xl font-semibold mb-4 text-center">Log In</h2>

        {error && (
          <div className="bg-red-100 text-red-700 text-sm p-2 rounded mb-4">
            {error}
          </div>
        )}

        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full px-4 py-2 mb-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-2 mb-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition disabled:opacity-50"
        >
          {isLoading ? "Logging in..." : "Log In"}
        </button>
      </form>
    </div>
  );
}
