import { useEffect, useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { checkCurrentUser, logoutUser } from "@/features/auth/authSlice";
import type { User } from '@/shared/types';
import type { AppDispatch } from '@/app/store';

// Redux state interface
interface RootState {
  auth: {
    isAuthenticated: boolean;
    user: User | null;
    isLoading: boolean;
  };
}

// Hook return type
interface UseAuthReturn {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  authChecked: boolean;
  handleLogout: () => Promise<void>;
}

/**
 * Custom hook for authentication management
 * Handles authentication state, checking, and logout functionality
 */
export const useAuth = (): UseAuthReturn => {
  const navigate = useNavigate();
  const dispatch = useDispatch<AppDispatch>();
  const { isAuthenticated, user, isLoading } = useSelector((state: RootState) => state.auth);
  const [authChecked, setAuthChecked] = useState<boolean>(false);

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

  const handleLogout = async (): Promise<void> => {
    try {
      await dispatch(logoutUser());
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