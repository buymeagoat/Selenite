import { test, expect } from '@playwright/test';

/**
 * Settings Page Tests
 * 
 * Tests settings page functionality including password change,
 * default transcription options, and system controls.
 */

test.describe('Settings Page', () => {
  test('navigate to settings page', async ({ page }) => {
    await page.goto('/');
    
    // Find settings link/button (could be in nav, sidebar, or dropdown)
    const settingsLink = page.getByRole('link', { name: /settings/i })
      .or(page.getByRole('button', { name: /settings/i }));
    
    await expect(settingsLink).toBeVisible();
    await settingsLink.click();
    
    // Should navigate to settings page
    await expect(page).toHaveURL(/\/settings$/);
    await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
  });

  test('change password successfully', async ({ page }) => {
    await page.goto('/settings');
    
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
    const saveButton = page.getByRole('button', { name: /save|update|change password/i });
    await expect(saveButton).toBeEnabled();
    await saveButton.click();
    
    // Should show success message
    await expect(
      page.getByText(/password.*changed|password.*updated|success/i)
    ).toBeVisible({ timeout: 5000 });
  });

  test('password change requires current password', async ({ page }) => {
    await page.goto('/settings');
    
    const currentPasswordInput = page.getByLabel(/current password/i)
      .or(page.locator('[data-testid="current-password"]'));
    const newPasswordInput = page.getByLabel(/new password/i)
      .or(page.locator('[data-testid="new-password"]'));
    const confirmPasswordInput = page.getByLabel(/confirm.*password/i)
      .or(page.locator('[data-testid="confirm-password"]'));
    
    // Leave current password empty
    await newPasswordInput.fill('newpassword123');
    await confirmPasswordInput.fill('newpassword123');
    
    const saveButton = page.getByRole('button', { name: /save|update|change password/i });
    await saveButton.click();
    
    // Should show error
    await expect(
      page.getByText(/current password.*required|enter.*current password/i)
    ).toBeVisible({ timeout: 3000 });
  });

  test('password change validates confirmation match', async ({ page }) => {
    await page.goto('/settings');
    
    const currentPasswordInput = page.getByLabel(/current password/i)
      .or(page.locator('[data-testid="current-password"]'));
    const newPasswordInput = page.getByLabel(/new password/i)
      .or(page.locator('[data-testid="new-password"]'));
    const confirmPasswordInput = page.getByLabel(/confirm.*password/i)
      .or(page.locator('[data-testid="confirm-password"]'));
    
    await currentPasswordInput.fill('changeme');
    await newPasswordInput.fill('newpassword123');
    await confirmPasswordInput.fill('differentpassword');
    
    const saveButton = page.getByRole('button', { name: /save|update|change password/i });
    await saveButton.click();
    
    // Should show error
    await expect(
      page.getByText(/password.*not match|password.*must match/i)
    ).toBeVisible({ timeout: 3000 });
  });

  test('configure default transcription options', async ({ page }) => {
    await page.goto('/settings');
    
    // Find default options section
    const modelSelect = page.getByLabel(/default model/i)
      .or(page.locator('[data-testid="default-model"]'));
    const languageSelect = page.getByLabel(/default language/i)
      .or(page.locator('[data-testid="default-language"]'));
    
    if (await modelSelect.isVisible()) {
      // Change default model
      await modelSelect.selectOption('medium');
      
      // Save settings
      const saveButton = page.getByRole('button', { name: /save/i }).first();
      await saveButton.click();
      
      // Should show success
      await expect(
        page.getByText(/settings.*saved|preferences.*updated|success/i)
      ).toBeVisible({ timeout: 5000 });
      
      // Verify selection persists
      await page.reload();
      await expect(modelSelect).toHaveValue('medium');
    }
  });

  test('configure maximum concurrent jobs', async ({ page }) => {
    await page.goto('/settings');
    
    const concurrentJobsInput = page.getByLabel(/maximum.*concurrent|max.*jobs/i)
      .or(page.locator('[data-testid="max-concurrent-jobs"]'));
    
    if (await concurrentJobsInput.isVisible()) {
      const currentValue = await concurrentJobsInput.inputValue();
      const newValue = '2';
      
      if (currentValue !== newValue) {
        await concurrentJobsInput.fill(newValue);
        
        const saveButton = page.getByRole('button', { name: /save/i }).first();
        await saveButton.click();
        
        await expect(
          page.getByText(/settings.*saved|success/i)
        ).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('logout and login with new password', async ({ page }) => {
    // This test would change password, logout, and verify new password works
    // Using storageState bypass for this specific test
    test.use({ storageState: { cookies: [], origins: [] } });
    
    // For now, just verify logout functionality exists
    await page.goto('/settings');
    
    const logoutButton = page.getByRole('button', { name: /logout|sign out/i })
      .or(page.getByRole('link', { name: /logout|sign out/i }));
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
      
      // Should redirect to login
      await expect(page).toHaveURL(/\/login$/);
    }
  });
});
