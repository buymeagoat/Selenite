import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactElement;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { token, isLoading } = useAuth();
  
  // Wait for auth state to restore from localStorage
  if (isLoading) {
    return null; // or a loading spinner
  }
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};
