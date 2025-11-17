import { test, expect } from '@playwright/test';

/**
 * Login Flow Tests
 * 
 * Tests authentication flows without using storageState.
 * Other tests will use pre-authenticated state from auth.setup.ts
 */

test.describe('Login Flow', () => {
  test.use({ storageState: { cookies: [], origins: [] } }); // No auth state

  test('user can login with valid credentials and reach dashboard', async ({ page }) => {
    await page.goto('/login');
    
    // Fill login form
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('changeme');
    
    const loginButton = page.getByRole('button', { name: /login/i });
    await expect(loginButton).toBeEnabled();
    await loginButton.click();
    
    // Should redirect to dashboard
    await page.waitForURL('**/');
    await expect(page).toHaveURL(/\/$/);
    
    // Verify dashboard elements are visible
    await expect(page.getByRole('heading', { name: /transcriptions/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /new transcription/i })).toBeVisible();
  });

  test('login fails with invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    await page.getByLabel('Username').fill('admin');
    await page.getByLabel('Password').fill('wrongpassword');
    
    await page.getByRole('button', { name: /login/i }).click();
    
    // Should show error message
    await expect(page.getByText(/invalid credentials/i)).toBeVisible();
    
    // Should stay on login page
    await expect(page).toHaveURL(/\/login$/);
  });

  test('protected routes redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/');
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login$/);
  });
});
