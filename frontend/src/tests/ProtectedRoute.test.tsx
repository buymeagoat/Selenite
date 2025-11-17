import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProtectedRoute } from '../components/layout/ProtectedRoute';
import { AuthProvider } from '../context/AuthContext';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const ProtectedContent = () => <div>Protected Area</div>;
const LoginPage = () => <div>Login Page</div>;

describe('ProtectedRoute', () => {
  it('redirects unauthenticated users to /login', () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}> 
          <Routes>
            <Route path="/" element={<ProtectedRoute><ProtectedContent /></ProtectedRoute>} />
            <Route path="/login" element={<LoginPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );
    expect(screen.queryByText('Protected Area')).not.toBeInTheDocument();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });
});
