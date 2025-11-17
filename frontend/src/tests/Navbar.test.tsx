import React, { useEffect } from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { Navbar } from '../components/layout/Navbar';

// Helper component to preset auth state
const AuthPreset: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { login } = useAuth();
  
  useEffect(() => {
    login('token', { username: 'alice', email: 'alice@example.com' });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run once on mount
  
  return <>{children}</>;
};

const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <AuthPreset>{children}</AuthPreset>
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
});
