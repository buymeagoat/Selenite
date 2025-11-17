import { test, expect } from '@playwright/test';
import { uiLogin } from './fixtures/auth';

// Basic smoke test for login flow.

test.describe('Login Flow', () => {
  test('user can login and reach protected app root', async ({ page }) => {
    await uiLogin(page);
    // Expect some element from protected app (navbar or root container) - adapt when available.
    await expect(page).toHaveURL(/\/$/);
  });
});
