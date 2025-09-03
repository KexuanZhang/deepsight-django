import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { signupUser } from "../authSlice";
import { config } from "@/config";
import type { AppDispatch, RootState } from "@/app/store";

// helper to read CSRF token from cookies
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  const value = match?.[2];
  return value ? decodeURIComponent(value) : null;
}

export default function SignupPage() {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { isLoading, error, isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  // fetch CSRF (Django sets it automatically on first GET to any view)
  useEffect(() => {
    // make a cheap GET to set the csrftoken cookie
    fetch(`${config.API_BASE_URL}/users/csrf/`, {
      credentials: "include"
    }).catch(() => {});
  }, []);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    // Check if passwords match before submitting
    if (password !== passwordConfirm) {
      return;
    }

    // Prepare the data for the signup request
    const signupData = {
      username,
      email,
      password,


    // Dispatch the signup action with the payload
      password_confirm: passwordConfirm,
    };

    // Dispatch the signup action with the prepared data
    dispatch(signupUser(signupData));
  };

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/"); // Redirect to the homepage if the user is authenticated
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="flex justify-center items-center h-screen bg-gray-50">
      <form
        onSubmit={handleSignup}
        className="bg-white p-8 rounded-lg shadow-md w-full max-w-sm"
      >
        <h2 className="text-xl font-semibold mb-4 text-center">Sign Up</h2>

        {(error || (password !== passwordConfirm && passwordConfirm !== "")) && (
          <div className="bg-red-100 text-red-700 text-sm p-2 rounded mb-4">
            {password !== passwordConfirm && passwordConfirm !== "" ? "Passwords do not match." : error}
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
          className="w-full px-4 py-2 mb-3 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <input
          type="password"
          placeholder="Confirm Password"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          className="w-full px-4 py-2 mb-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          required
        />

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-red-600 text-white py-2 rounded hover:bg-red-700 transition disabled:opacity-50"
        >
          {isLoading ? "Signing up..." : "Sign Up"}
        </button>
      </form>
    </div>
  );
}
