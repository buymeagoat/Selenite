import React from 'react';
import { Navbar } from './components/layout/Navbar';
import { Dashboard } from './pages/Dashboard';

const App: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-sage-light">
      <Navbar />
      <main className="flex-1">
        <Dashboard />
      </main>
    </div>
  );
};

export default App;
