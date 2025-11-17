import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Login } from '../pages/Login';
import { AuthProvider } from '../context/AuthContext';
import { MemoryRouter, useNavigate } from 'react-router-dom';

// Simple wrapper to provide router context
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <MemoryRouter>{children}</MemoryRouter>
  </AuthProvider>
);

describe('Login Page', () => {
  it('renders form fields and disabled button initially', () => {
    render(<Login />, { wrapper: Wrapper });
    expect(screen.getByText(/Selenite Login/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    const button = screen.getByRole('button', { name: /login/i });
    expect(button).toBeDisabled();
  });

  it('enables login button when username and password provided', () => {
    render(<Login />, { wrapper: Wrapper });
    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: 'alice' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'secret' } });
    const button = screen.getByRole('button', { name: /login/i });
    expect(button).not.toBeDisabled();
  });
});
