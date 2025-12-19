import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Settings as SettingsIcon, Menu, X, Shield } from 'lucide-react';

type Page = 'dashboard' | 'settings' | 'admin';

interface NavbarProps {
  onNavigate?: (page: Page) => void;
  activePage?: Page;
}

export const Navbar: React.FC<NavbarProps> = ({ onNavigate, activePage }) => {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const initials = user ? user.username.slice(0, 2).toUpperCase() : '?';
  const isAdmin = Boolean(user?.is_admin);

  return (
    <header className="bg-white border-b border-sage-mid px-4 py-3 flex items-center justify-between">
      <button
        onClick={() => {
          onNavigate?.('dashboard');
          setMobileMenuOpen(false);
        }}
        className="text-xl font-semibold transition"
        style={{ color: activePage === 'dashboard' ? '#0b5a3c' : '#0f2e1f' }}
      >
        Selenite
      </button>
      
      {/* Desktop Navigation */}
      <div className="hidden md:flex items-center gap-3">
        {onNavigate && (
          <button
            onClick={() => onNavigate('settings')}
            className={`p-2 rounded transition hover:bg-sage-light ${
              activePage === 'settings' ? 'text-forest-green bg-sage-light' : 'text-pine-mid hover:text-forest-green'
            }`}
            aria-label="Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </button>
        )}
        {onNavigate && isAdmin && (
          <button
            onClick={() => onNavigate('admin')}
            className={`p-2 rounded transition hover:bg-sage-light ${
              activePage === 'admin' ? 'text-forest-green bg-sage-light' : 'text-pine-mid hover:text-forest-green'
            }`}
            aria-label="Admin"
          >
            <Shield className="w-5 h-5" />
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

      {/* Mobile Menu Button */}
      <button
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        className="md:hidden p-2 text-pine-mid hover:text-forest-green transition"
        aria-label="Toggle menu"
      >
        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-14 left-0 right-0 bg-white border-b border-sage-mid shadow-lg z-20 animate-fade-in">
          <div className="flex flex-col p-4">
            <div className="flex items-center gap-3 mb-4 pb-4 border-b border-sage-mid">
              <div className="w-10 h-10 rounded-full bg-pine-mid text-white flex items-center justify-center font-medium">
                {initials}
              </div>
              <div>
                <div className="text-sm font-medium text-pine-deep">{user?.username}</div>
                <div className="text-xs text-pine-mid">{user?.email}</div>
              </div>
            </div>
            {onNavigate && (
              <>
                <button
                  onClick={() => {
                    onNavigate('dashboard');
                    setMobileMenuOpen(false);
                  }}
                  className={`flex items-center gap-2 px-3 py-2 rounded text-left ${
                    activePage === 'dashboard'
                      ? 'bg-sage-light text-forest-green'
                      : 'hover:bg-sage-light text-pine-deep'
                  }`}
                >
                  <span>Dashboard</span>
                </button>
                <button
                  onClick={() => {
                    onNavigate('settings');
                    setMobileMenuOpen(false);
                  }}
                  className={`flex items-center gap-2 px-3 py-2 rounded text-left ${
                    activePage === 'settings'
                      ? 'bg-sage-light text-forest-green'
                      : 'hover:bg-sage-light text-pine-deep'
                  }`}
                >
                  <SettingsIcon className="w-5 h-5" />
                  <span>Settings</span>
                </button>
                {isAdmin && (
                  <button
                    onClick={() => {
                      onNavigate('admin');
                      setMobileMenuOpen(false);
                    }}
                    className={`flex items-center gap-2 px-3 py-2 rounded text-left ${
                      activePage === 'admin'
                        ? 'bg-sage-light text-forest-green'
                        : 'hover:bg-sage-light text-pine-deep'
                    }`}
                  >
                    <Shield className="w-5 h-5" />
                    <span>Admin</span>
                  </button>
                )}
              </>
            )}
            <button
              onClick={() => {
                logout();
                setMobileMenuOpen(false);
              }}
              className="flex items-center gap-2 px-3 py-2 rounded hover:bg-sage-light text-terracotta text-left mt-2 border-t border-sage-mid pt-4"
            >
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
