import React from 'react';

interface ToastProps {
  type: 'success' | 'error' | 'info';
  message: string;
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ type, message, onClose }) => {
  const bgColors = {
    success: 'bg-green-500',
    error: 'bg-terracotta',
    info: 'bg-forest-green'
  };

  const icons = {
    success: '✓',
    error: '✕',
    info: 'ⓘ'
  };

  return (
    <div className={`${bgColors[type]} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 min-w-[300px] max-w-md animate-slide-in`}>
      <span className="text-xl font-bold">{icons[type]}</span>
      <span className="flex-1 text-sm">{message}</span>
      <button
        onClick={onClose}
        className="ml-2 hover:opacity-75 transition font-bold text-lg"
        aria-label="Close"
      >
        ×
      </button>
    </div>
  );
};

interface ToastContainerProps {
  toasts: Array<{ id: string; type: 'success' | 'error' | 'info'; message: string }>;
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map(toast => (
        <Toast key={toast.id} type={toast.type} message={toast.message} onClose={() => onDismiss(toast.id)} />
      ))}
    </div>
  );
};
