import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import type { ProxyOptions } from 'vite';

const apiProxyTarget = process.env.BACKEND_URL || 'http://127.0.0.1:8100';

const proxyConfig: Record<string, string | ProxyOptions> = {
  '/api': {
    target: apiProxyTarget,
    changeOrigin: true,
    secure: false,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: proxyConfig,
  },
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
