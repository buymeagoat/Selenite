import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Settings } from './pages/Settings';
import { Admin } from './pages/Admin';
import { ToastProvider } from './context/ToastContext';
import { useAuth } from './context/AuthContext';

type Page = 'dashboard' | 'settings' | 'admin';

const App: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const currentPage: Page =
    location.pathname === '/settings' ? 'settings' : location.pathname === '/admin' ? 'admin' : 'dashboard';

  const handleNavigate = (page: Page) => {
    if (page === 'settings') {
      navigate('/settings');
    } else if (page === 'admin') {
      navigate('/admin');
    } else {
      navigate('/');
    }
  };

  useEffect(() => {
    if (user?.force_password_reset && location.pathname !== '/settings') {
      navigate('/settings');
    }
  }, [user?.force_password_reset, location.pathname, navigate]);

  return (
    <ToastProvider>
      <div className="min-h-screen flex flex-col bg-sage-light">
        <Navbar onNavigate={handleNavigate} activePage={currentPage} />
        <main className="flex-1">
          {currentPage === 'dashboard' && <Dashboard />}
          {currentPage === 'settings' && <Settings />}
          {currentPage === 'admin' && <Admin />}
        </main>
      </div>
    </ToastProvider>
  );
};

export default App;
