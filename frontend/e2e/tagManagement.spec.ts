import { test, expect, Page } from '@playwright/test';

// Helpers
const openSettings = async (page: Page) => {
  await page.goto('/');
  const settingsButton = page.getByRole('button', { name: /^settings$/i }).first();
  if (await settingsButton.isVisible({ timeout: 2000 }).catch(() => false)) {
    await settingsButton.click();
    await page.waitForURL(/\/settings/, { timeout: 5000 });
    await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
    return;
  }
  const toggle = page.getByLabel(/toggle menu/i);
  await toggle.click();
  const mobileSettings = page.getByRole('button', { name: /^settings$/i }).last();
  await expect(mobileSettings).toBeVisible();
  await mobileSettings.click();
  await page.waitForURL(/\/settings/, { timeout: 5000 });
  await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();
};

test.describe('Tag Management (prod-parity)', () => {
  test('view tag inventory through settings', async ({ page }) => {
    await openSettings(page);
    await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible();

    const tagsSection = page.getByRole('button', { name: /tags/i });
    await expect(tagsSection).toBeVisible({ timeout: 8000 });
    const tagsContentLocator = page.locator('[data-testid="settings-tags-content"]').first();
    const contentCount = await tagsContentLocator.count();
    const isContentVisible = contentCount > 0 ? await tagsContentLocator.isVisible() : false;
    if (!isContentVisible) {
      await tagsSection.click();
    }
    await page.waitForSelector('[data-testid="settings-tags-loaded"]', { timeout: 10000 });

    const tagsContent = page.locator('[data-testid="settings-tags-loaded"] [data-testid="tag-list"]').first();
    // Accept either populated list or empty-state rendered inside the tags section
    await tagsContent.scrollIntoViewIfNeeded();
    await expect(tagsContent).toBeVisible({ timeout: 10000 });
    const tagName = tagsContent.locator('[data-testid="tag-name"]').first();
    const tagCount = await tagName.count();
    if (tagCount > 0) {
      await expect(tagName).toBeVisible({ timeout: 10000 });
    } else {
      await expect(tagsContent).toContainText(/No tags created yet/i, { timeout: 5000 });
    }
  });

  test('assign tag to job from job detail', async ({ page }) => {
    await page.goto('/');

    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible({ timeout: 10000 });
    await jobCard.click();

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    const tagInput = modal.locator('[data-testid="tag-input"]');
    await expect(tagInput).toBeVisible();

    const newTagName = `TestTag-${Date.now()}`;
    await tagInput.fill(newTagName);
    const addButton = modal.getByRole('button', { name: /^add tag$/i });
    await expect(addButton).toBeEnabled();
    await addButton.click();

    await expect(modal.locator('[data-testid="tag-chip"]', { hasText: newTagName })).toBeVisible();
  });

  test('filter jobs by tag', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="job-card"]').first()).toBeVisible({ timeout: 10000 });

    const tagFilterBtn = page.locator('[data-testid="tag-filter-button"]');
    await expect(tagFilterBtn).toBeVisible({ timeout: 5000 });
    await tagFilterBtn.click();

    const firstTagOption = page.locator('[data-testid="tag-filter-option"]').first();
    await expect(firstTagOption).toBeVisible({ timeout: 5000 });
    const optionLabel = await firstTagOption.evaluate((el) => (el as HTMLInputElement).ariaLabel);
    await firstTagOption.click();

    await page.waitForTimeout(500);

    const visibleJobs = page.locator('[data-testid="job-card"]');
    const count = await visibleJobs.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < Math.min(count, 3); i++) {
      await expect(visibleJobs.nth(i).locator('[data-testid="job-tags"]')).toContainText(optionLabel ?? '', { timeout: 2000 });
    }
  });

  test('remove tag from job', async ({ page }) => {
    await page.goto('/');

    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible({ timeout: 10000 });
    await jobCard.click();

    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    // Ensure at least one tag exists by creating one, then remove it
    const tagInput = modal.locator('[data-testid="tag-input"]');
    await expect(tagInput).toBeVisible();
    const tempTag = `Removable-${Date.now()}`;
    await tagInput.fill(tempTag);
    const addButton = modal.getByRole('button', { name: /^add tag$/i });
    await expect(addButton).toBeEnabled();
    await addButton.click();

    const tagChips = modal.locator('[data-testid="tag-chip"]');
    await expect(tagChips.filter({ hasText: tempTag }).first()).toBeVisible({ timeout: 10000 });

    const removeButton = tagChips.filter({ hasText: tempTag }).first().locator('[data-testid="remove-tag"]');
    await expect(removeButton).toBeVisible({ timeout: 2000 });
    await removeButton.click();

    const removedChip = tagChips.filter({ hasText: tempTag });
    await expect(removedChip).toHaveCount(0, { timeout: 10000 });
  });
});
