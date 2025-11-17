import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['src/tests/setupMocks.ts'],
    globals: true,
    reporters: 'default'
  },
});
