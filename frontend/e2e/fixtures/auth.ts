import { Page, expect } from '@playwright/test';

export async function uiLogin(page: Page, username = 'admin', password = 'changeme') {
  await page.goto('/login');
  // Fill fields by label (robust against minor DOM changes)
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  const loginButton = page.getByRole('button', { name: /login/i });
  await expect(loginButton).toBeEnabled();
  await loginButton.click();
  // After placeholder auth, we navigate to '/'
  await page.waitForURL('**/');
  await expect(page).toHaveURL(/\/$/);
}

// Persist authenticated state to speed up later tests.
export async function ensureStorageState(page: Page, storagePath = '.auth/admin.json') {
  await uiLogin(page);
  await page.context().storageState({ path: storagePath });
}
