import React, { useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Settings } from './pages/Settings';
import { ToastProvider } from './context/ToastContext';

type Page = 'dashboard' | 'settings';

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');

  return (
    <ToastProvider>
      <div className="min-h-screen flex flex-col bg-sage-light">
        <Navbar onNavigate={setCurrentPage} />
        <main className="flex-1">
          {currentPage === 'dashboard' && <Dashboard />}
          {currentPage === 'settings' && <Settings />}
        </main>
      </div>
    </ToastProvider>
  );
};

export default App;
