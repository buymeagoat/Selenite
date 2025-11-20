import { defineConfig, devices } from '@playwright/test';

// Base URL: use Vite dev by default; can override via BASE_URL env.
const baseURL = process.env.BASE_URL || 'http://localhost:5173';
const shouldStartServers = !process.env.SKIP_WEB_SERVER;
const webServer = shouldStartServers
  ? [
      {
        command: 'node ../scripts/start-backend-e2e.js',
        port: 8100,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000
      },
      {
        command: 'npm run start:prod',
        port: 5173,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000
      }
    ]
  : undefined;

export default defineConfig({
  testDir: './e2e',
  timeout: 60 * 1000,
  expect: { timeout: 5000 },
  // Disable full parallelism across projects to avoid shared mutable state issues
  // (e.g., password change test altering admin credentials mid-run for other browsers).
  // Individual tests within a project can still run in parallel via workers.
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]] : [['list'], ['html', { open: 'never' }]],
  webServer,
  use: {
    baseURL,
    actionTimeout: 30_000,
    navigationTimeout: 45_000,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    // Setup project to generate authenticated state
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/
    },
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        storageState: '.auth/admin.json'
      },
      dependencies: ['setup']
    },
    {
      name: 'firefox',
      use: { 
        ...devices['Desktop Firefox'],
        storageState: '.auth/admin.json'
      },
      dependencies: ['setup']
    },
    {
      name: 'webkit',
      use: { 
        ...devices['Desktop Safari'],
        storageState: '.auth/admin.json'
      },
      dependencies: ['setup']
    }
  ],
  outputDir: 'test-results'
});
