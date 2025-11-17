import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Settings as SettingsIcon } from 'lucide-react';

interface NavbarProps {
  onNavigate?: (page: 'dashboard' | 'settings') => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigate }) => {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const initials = user ? user.username.slice(0, 2).toUpperCase() : '?';

  return (
    <header className="bg-white border-b border-sage-mid px-4 py-3 flex items-center justify-between">
      <button
        onClick={() => onNavigate?.('dashboard')}
        className="text-forest-green text-xl font-semibold hover:opacity-80 transition"
      >
        Selenite
      </button>
      <div className="flex items-center gap-3">
        {onNavigate && (
          <button
            onClick={() => onNavigate('settings')}
            className="p-2 text-pine-mid hover:text-forest-green transition rounded hover:bg-sage-light"
            aria-label="Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </button>
        )}
        <div className="relative">
          <button
            onClick={() => setOpen((o) => !o)}
            aria-haspopup="true"
            aria-expanded={open}
            className="w-10 h-10 rounded-full bg-pine-mid text-white flex items-center justify-center font-medium"
          >
            {initials}
          </button>
          {open && (
            <div className="absolute right-0 mt-2 w-40 bg-white shadow rounded p-2 z-10">
              <div className="px-2 py-1 text-sm text-pine-mid">{user?.email}</div>
              <button
                onClick={() => { logout(); setOpen(false); }}
                className="text-left w-full px-2 py-2 rounded hover:bg-sage-light text-sm text-pine-deep"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
