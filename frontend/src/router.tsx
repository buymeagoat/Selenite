import React from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import { Login } from './pages/Login';
import { TranscriptView } from './pages/TranscriptView';
import { ProtectedRoute } from './components/layout/ProtectedRoute';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <App />
      </ProtectedRoute>
    ),
  },
  {
    path: '/transcripts/:jobId',
    element: (
      <ProtectedRoute>
        <TranscriptView />
      </ProtectedRoute>
    ),
  },
]);

export const AppRouter: React.FC = () => <RouterProvider router={router} />;
