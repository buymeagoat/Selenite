import React from 'react';
import { Navbar } from './components/layout/Navbar';

const App: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-sage-light">
      <Navbar />
      <main className="flex-1 px-6 py-6">
        <h1 className="text-3xl font-semibold text-pine-deep mb-4">Dashboard</h1>
        <p className="text-pine-mid">Welcome to Selenite. More content coming soon.</p>
      </main>
    </div>
  );
};

export default App;
