import { Page, expect } from '@playwright/test';

async function waitForDashboard(page: Page, maxMs = 35000) {
  // First, wait for navigation to root (non-fatal if already there)
  try {
    await page.waitForURL('**/', { timeout: maxMs / 2 });
  } catch {
    // Might already be on the page or redirected differently; continue
  }

  // Robust multi-attempt strategy: check heading visibility with incremental delays
  const heading = page.getByRole('heading', { name: /transcriptions/i });
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    if (/\/$/ .test(page.url())) {
      if (await heading.isVisible().catch(() => false)) {
        return;
      }
    }
    // Allow React hydration + ProtectedRoute resolution
    await page.waitForTimeout(400);
  }
  // Final explicit check before failing
  await heading.waitFor({ state: 'visible', timeout: 2000 }).catch(() => {
    throw new Error('Dashboard not reached within timeout; last URL=' + page.url());
  });
}

export async function uiLogin(page: Page, username = 'admin', password = 'changeme') {
  await page.goto('/login', { waitUntil: 'domcontentloaded' });
  // Fill fields by label (robust against minor DOM changes)
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  const loginButton = page.getByRole('button', { name: /login/i });
  await expect(loginButton).toBeEnabled();
  await loginButton.click();
  // Progressive dashboard wait
  await waitForDashboard(page);
  await expect(page).toHaveURL(/\/$/);
  
  // Wait a moment for localStorage to be set
  await page.waitForTimeout(500);
}

// Persist authenticated state to speed up later tests.
export async function ensureStorageState(page: Page, storagePath = '.auth/admin.json') {
  await uiLogin(page);
  await page.context().storageState({ path: storagePath });
}
