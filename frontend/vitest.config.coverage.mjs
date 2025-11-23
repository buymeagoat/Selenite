import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      reporter: ['text', 'json-summary'],
      lines: 70,
      statements: 70,
      functions: 70,
      branches: 60,
    },
  },
});
