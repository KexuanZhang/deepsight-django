// src/pages/SignupPage.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function SignupPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");

    try {
      // ▶︎ Make sure this URL points at your FastAPI backend, not the Vite dev server!
      const response = await fetch("http://localhost:8000/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });

      // If signup fails (4xx/5xx), try to parse a JSON error; otherwise show fallback
      if (!response.ok) {
        let errMsg = "Signup failed. Please try again.";
        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
          const errJson = await response.json().catch(() => null);
          if (errJson && errJson.detail) {
            errMsg = errJson.detail;
          }
        }
        setError(errMsg);
        return;
      }

      // At this point, response.ok === true. Try parsing JSON (it should have { message, user_id, username })
      const contentType = response.headers.get("content-type") || "";
      let data = null;
      if (contentType.includes("application/json")) {
        data = await response.json().catch(() => null);
      }

      if (!data || !data.user_id) {
        setError("Signup succeeded but no user data was returned.");
        return;
      }

      // Optionally: auto‐log in the user by storing a token if your backend returned one.
      // In this example, FastAPI's /signup returns just { message, user_id, username },
      // so we redirect the user to /login to enter credentials again.
      navigate("/login");
    } catch (err) {
      console.error(err);
      setError("Network error. Please try again.");
    }
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-50">
      <form
        onSubmit={handleSignup}
        className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm"
      >
        <h2 className="text-xl font-semibold mb-4 text-center">Sign Up</h2>

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
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
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
          className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition"
        >
          Sign Up
        </button>
      </form>
    </div>
  );
}
