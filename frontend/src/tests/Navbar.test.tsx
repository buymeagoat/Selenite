import React, { useEffect } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { Navbar } from '../components/layout/Navbar';

// Helper component to preset auth state
const AuthPreset: React.FC<{ children: React.ReactNode; isAdmin?: boolean }> = ({ children, isAdmin = true }) => {
  const { login } = useAuth();
  
  useEffect(() => {
    login('token', {
      id: 1,
      username: 'alice',
      email: 'alice@example.com',
      is_admin: isAdmin,
      is_disabled: false,
      force_password_reset: false,
      is_email_verified: true,
      last_login_at: null,
      created_at: new Date().toISOString()
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run once on mount
  
  return <>{children}</>;
};

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <AuthPreset>{children}</AuthPreset>
  </AuthProvider>
);

const NonAdminWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <AuthPreset isAdmin={false}>{children}</AuthPreset>
  </AuthProvider>
);

describe('Navbar', () => {
  it('shows brand and user initials', () => {
    render(<Navbar />, { wrapper: Wrapper });
    expect(screen.getByText('Selenite')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /AL/i })).toBeInTheDocument();
  });

  it('opens menu and shows email then logs out', () => {
    render(<Navbar />, { wrapper: Wrapper });
    const avatar = screen.getByRole('button', { name: /AL/i });
    fireEvent.click(avatar);
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Logout'));
    // After logout avatar should now show '?' initials when re-opened
    fireEvent.click(avatar);
    expect(screen.getByRole('button', { name: /\?/i })).toBeInTheDocument();
  });

  it('renders admin navigation button for admins', () => {
    const handleNavigate = vi.fn();
    render(<Navbar onNavigate={handleNavigate} activePage="admin" />, { wrapper: Wrapper });
    const adminButton = screen.getByRole('button', { name: /Admin/i });
    fireEvent.click(adminButton);
    expect(handleNavigate).toHaveBeenCalledWith('admin');
  });

  it('hides admin button for non-admin users', () => {
    render(<Navbar onNavigate={vi.fn()} activePage="dashboard" />, { wrapper: NonAdminWrapper });
    expect(screen.queryByRole('button', { name: /Admin/i })).not.toBeInTheDocument();
  });
});
