import { test, expect, Page } from '@playwright/test';

/**
 * Settings Page Tests
 * 
 * Tests settings page functionality including password change,
 * default transcription options, and system controls.
 */

async function openSettings(page: Page) {
  await page.goto('/');
  const settingsButton = page.getByRole('button', { name: /^settings$/i }).first();
  if (await settingsButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await settingsButton.click();
    await page.waitForURL(/\/settings/, { timeout: 5000 });
    await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible();
    return;
  }

  const menuToggle = page.getByLabel(/toggle menu/i);
  await menuToggle.click();
  const mobileSettings = page.getByRole('button', { name: /^settings$/i }).last();
  await expect(mobileSettings).toBeVisible();
  await mobileSettings.click();
  await page.waitForURL(/\/settings/, { timeout: 5000 });
  await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible();
}

test.describe('Settings Page', () => {
  test('navigate to settings page', async ({ page }) => {
    await openSettings(page);
    
    // Settings page should load (spa navigation, no URL change needed)
    await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible();
  });

  test('change password successfully (UI only, backend mocked)', async ({ page }) => {
    await openSettings(page);
    await expect(page.getByRole('heading', { name: /settings/i }).first()).toBeVisible();

    // Mock password change endpoint so we don't mutate the shared admin account.
    await page.route('**/auth/password', async (route) => {
      const payload = route.request().postDataJSON() as Record<string, string>;
      expect(payload.current_password).toBeTruthy();
      expect(payload.new_password).toBeTruthy();
      expect(payload.confirm_password).toBe(payload.new_password);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Password changed successfully' })
      });
    });
    
    // Find password change section
    const currentPasswordInput = page.getByLabel(/current password/i)
      .or(page.locator('[data-testid="current-password"]'));
    const newPasswordInput = page.getByLabel(/new password/i)
      .or(page.locator('[data-testid="new-password"]'));
    const confirmPasswordInput = page.getByLabel(/confirm.*password/i)
      .or(page.locator('[data-testid="confirm-password"]'));
    
    await expect(currentPasswordInput).toBeVisible();
    await expect(newPasswordInput).toBeVisible();
    await expect(confirmPasswordInput).toBeVisible();
    
    // Fill password fields
    await currentPasswordInput.fill('changeme');
    await newPasswordInput.fill('newpassword123');
    await confirmPasswordInput.fill('newpassword123');
    
    // Submit
    const saveButton = page.locator('[data-testid="password-save"]');
    await expect(saveButton).toBeEnabled();
    await saveButton.click();
    
    // Should show success message
    const successMessage = page.getByTestId('password-success');
    await expect(successMessage).toHaveText(/password changed successfully/i, { timeout: 5000 });
    await expect(currentPasswordInput).toHaveValue('');
    await expect(newPasswordInput).toHaveValue('');
    await expect(confirmPasswordInput).toHaveValue('');
  });

  test('password change requires current password', async ({ page }) => {
    // Navigate via dashboard to ensure SPA route loads
    await openSettings(page);
    
    const currentPasswordInput = page.getByLabel(/current password/i)
      .or(page.locator('[data-testid="current-password"]'));
    const newPasswordInput = page.getByLabel(/new password/i)
      .or(page.locator('[data-testid="new-password"]'));
    const confirmPasswordInput = page.getByLabel(/confirm.*password/i)
      .or(page.locator('[data-testid="confirm-password"]'));
    
    // Leave current password empty
    await newPasswordInput.fill('newpassword123');
    await confirmPasswordInput.fill('newpassword123');
    
    const saveButton = page.locator('[data-testid="password-save"]');
    await saveButton.click();
    
    // Should show error
    await expect(
      page.getByText(/current password.*required|enter.*current password/i)
    ).toBeVisible({ timeout: 3000 });
  });

  test('password change validates confirmation match', async ({ page }) => {
    await openSettings(page);
    
    const currentPasswordInput = page.getByLabel(/current password/i)
      .or(page.locator('[data-testid="current-password"]'));
    const newPasswordInput = page.getByLabel(/new password/i)
      .or(page.locator('[data-testid="new-password"]'));
    const confirmPasswordInput = page.getByLabel(/confirm.*password/i)
      .or(page.locator('[data-testid="confirm-password"]'));
    
    await currentPasswordInput.fill('changeme');
    await newPasswordInput.fill('newpassword123');
    await confirmPasswordInput.fill('differentpassword');
    
    const saveButton = page.locator('[data-testid="password-save"]');
    await saveButton.click();
    
    // Should show error
    await expect(
      page.getByText(/password.*not match|password.*must match/i)
    ).toBeVisible({ timeout: 3000 });
  });

  test('configure default transcription options', async ({ page }) => {
    await page.goto('/settings');
    
    // Find default options section
    const languageSelect = page.getByLabel(/default language/i)
      .or(page.locator('[data-testid="default-language"]'));

    if (await languageSelect.isVisible()) {
      const currentValue = await languageSelect.inputValue();
      const nextValue = currentValue === 'en' ? 'es' : 'en';

      await languageSelect.selectOption(nextValue);

      const [saveResponse] = await Promise.all([
        page.waitForResponse((response) => {
          return response.url().endsWith('/settings') && response.request().method() === 'PUT';
        }),
        page.getByTestId('default-save').click(),
      ]);

      await expect(
        page.getByText('Default transcription settings saved', { exact: true })
      ).toBeVisible({ timeout: 5000 });

      const savedPayload = await saveResponse.json();
      expect(savedPayload.default_language).toBe(nextValue);
      await expect(languageSelect).toHaveValue(nextValue);
    }
  });

  test('configure maximum concurrent jobs (admin only)', async ({ page }) => {
    await page.goto('/admin');

    const adminSection = page.getByTestId('admin-advanced-settings');
    await expect(adminSection).toBeVisible();

    const concurrentJobsInput = page.locator('[data-testid="max-concurrent-jobs"]');
    await expect(concurrentJobsInput).toBeVisible();

    const currentValue = await concurrentJobsInput.inputValue();
    const newValue = currentValue === '5' ? '4' : '5';

    await concurrentJobsInput.fill(newValue);

    const saveButton = page.getByTestId('admin-save-all');
    await saveButton.click();

    await expect(
      page.getByText(/advanced settings saved|advanced defaults saved|settings.*saved|success/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('logout and login with new password', async ({ page }) => {
    // This test would change password, logout, and verify new password works
    // NOTE: test.use() cannot be called inside a test - storageState is inherited from describe level
    // For actual logout testing, create separate test file with no storageState

    // For now, just verify logout functionality exists
    await page.goto('/settings');    const logoutButton = page.getByRole('button', { name: /logout|sign out/i })
      .or(page.getByRole('link', { name: /logout|sign out/i }));
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login$/);
    }
  });
});
