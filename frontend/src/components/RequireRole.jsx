import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

/**
 * RequireRole restricts access based on the user's role.
 * It expects the required role to be stored in localStorage under `userRole`.
 */
const RequireRole = ({ role, children }) => {
  const location = useLocation();
  const userRole = localStorage.getItem('userRole');

  if (userRole?.toLowerCase() !== role.toLowerCase()) {
    return <Navigate to="/dashboard" replace state={{ from: location }} />;
  }

  return children;
};

export default RequireRole;
