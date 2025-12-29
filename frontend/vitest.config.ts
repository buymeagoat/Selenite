import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    setupFiles: ['src/tests/setupMocks.ts'],
    globals: true,
    reporters: 'default',
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**', '**/.{idea,git,cache,output,temp}/**'],
    pool: 'threads',
    maxWorkers: 1,
    fileParallelism: false,
    coverage: {
      provider: 'istanbul',
      all: false,
      reportsDirectory: 'coverage',
      reporter: ['text', 'json', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/tests/**',
        'src/**/__tests__/**',
        'src/**/setup*.ts',
        'e2e/**',
        'scripts/**',
      ],
    },
  },
});
