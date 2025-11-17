import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Placeholder auth flow: replace with API call to backend /auth/login
    if (username && password) {
      login('fake-jwt-token', { username, email: `${username}@example.com` });
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-sage-light">
      <form onSubmit={handleSubmit} className="bg-white shadow rounded p-6 w-full max-w-sm space-y-4">
        <h1 className="text-2xl font-semibold text-pine-deep">Selenite Login</h1>
        <div className="space-y-1">
          <label className="text-sm font-medium text-pine-mid" htmlFor="username">Username</label>
          <input
            id="username"
            className="border rounded px-3 py-2 w-full"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium text-pine-mid" htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            className="border rounded px-3 py-2 w-full"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
          />
        </div>
        <button
          type="submit"
          disabled={!username || !password}
          className="w-full bg-forest-green text-white py-2 rounded disabled:opacity-50"
        >
          Login
        </button>
      </form>
    </div>
  );
};
