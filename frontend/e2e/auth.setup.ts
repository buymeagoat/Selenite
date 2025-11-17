import { test as setup } from '@playwright/test';
import { ensureStorageState } from './fixtures/auth';

/**
 * Global setup: authenticate once and save state for reuse across all tests.
 * This runs before any other test in the suite.
 */
setup('authenticate', async ({ page }) => {
  await ensureStorageState(page, '.auth/admin.json');
});
