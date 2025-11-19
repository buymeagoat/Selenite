import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    globals: true,
    testTimeout: 5000,
    hookTimeout: 5000,
    teardownTimeout: 1000,
    isolate: true
  }
});
