import { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { checkCurrentUser, logoutUser } from '../../features/auth/authSlice';

/**
 * Custom hook for authentication management
 * Handles authentication state, checking, and logout functionality
 */
export const useAuth = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isAuthenticated, user, isLoading } = useSelector((state) => state.auth);
  const [authChecked, setAuthChecked] = useState(false);

  // Check authentication state on mount
  useEffect(() => {
    const checkAuth = async () => {
      await dispatch(checkCurrentUser());
      setAuthChecked(true);
    };
    checkAuth();
  }, [dispatch]);

  // Redirect to login if not authenticated (after auth check is complete)
  useEffect(() => {
    if (authChecked && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, authChecked, navigate]);

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      // Even if logout fails, redirect to login page
      navigate('/login');
    }
  };

  return {
    isAuthenticated,
    user,
    isLoading,
    authChecked,
    handleLogout,
  };
};