import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

const useLogout = () => {
  const navigate = useNavigate();
  return useCallback(() => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userRole');
    navigate('/');
  }, [navigate]);
};

export default useLogout;
