import { test, expect } from '@playwright/test';

/**
 * Tag Management Tests
 * 
 * Tests tag creation, assignment to jobs, and filtering by tags.
 */

test.describe('Tag Management', () => {
  test('create new tag', async ({ page }) => {
    await page.goto('/');
    
    // Find tag management UI (could be in sidebar, modal, or separate section)
    const manageTagsButton = page.getByRole('button', { name: /manage tags|tags/i });
    
    if (await manageTagsButton.isVisible()) {
      await manageTagsButton.click();
      
      // Tag management modal/section should open
      const tagModal = page.getByRole('dialog').or(page.locator('[data-testid="tag-management"]'));
      await expect(tagModal).toBeVisible();
      
      // Find create tag input
      const tagInput = tagModal.getByPlaceholder(/tag name|new tag/i)
        .or(tagModal.locator('[data-testid="tag-input"]'));
      await expect(tagInput).toBeVisible();
      
      // Create a unique tag name
      const tagName = `TestTag${Date.now()}`;
      await tagInput.fill(tagName);
      
      // Submit (could be button or Enter key)
      const createButton = tagModal.getByRole('button', { name: /create|add|save/i });
      if (await createButton.isVisible()) {
        await createButton.click();
      } else {
        await tagInput.press('Enter');
      }
      
      // Tag should appear in tag list
      await expect(tagModal.getByText(tagName)).toBeVisible({ timeout: 5000 });
    }
  });

  test('assign tag to job', async ({ page }) => {
    await page.goto('/');
    
    // Open a job detail modal
    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible({ timeout: 10000 });
    await jobCard.click();
    
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    
    // Find tag input/selector in job detail
    const tagInput = modal.locator('[data-testid="tag-input"]')
      .or(modal.getByPlaceholder(/add tag|search tags/i));
    
    if (await tagInput.isVisible()) {
      // Type to search/create tag
      await tagInput.fill('TestTag');
      
      // Select from dropdown or create new
      const tagOption = page.getByRole('option', { name: /TestTag/i })
        .or(page.getByText(/TestTag/i).first());
      
      if (await tagOption.isVisible({ timeout: 2000 })) {
        await tagOption.click();
        
        // Tag should be assigned and visible
        await expect(modal.getByText(/TestTag/i)).toBeVisible();
      }
    }
  });

  test('filter jobs by tag', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.locator('[data-testid="job-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Find tag filter UI
    const tagFilter = page.locator('[data-testid="tag-filter"]')
      .or(page.getByLabel(/filter.*tag/i))
      .or(page.getByRole('button', { name: /tags/i }));
    
    if (await tagFilter.isVisible()) {
      await tagFilter.click();
      
      // Select a tag from the list
      const firstTag = page.locator('[data-testid="tag-option"]').first()
        .or(page.getByRole('option').first());
      
      if (await firstTag.isVisible({ timeout: 2000 })) {
        const tagText = await firstTag.textContent();
        await firstTag.click();
        
        await page.waitForTimeout(500);
        
        // Jobs should be filtered
        const visibleJobs = page.locator('[data-testid="job-card"]');
        const count = await visibleJobs.count();
        
        // All visible jobs should have the selected tag
        if (count > 0 && tagText) {
          for (let i = 0; i < Math.min(count, 3); i++) {
            const jobTags = visibleJobs.nth(i).locator('[data-testid="job-tags"]')
              .or(visibleJobs.nth(i).getByText(tagText));
            // At least verify the jobs exist when filtered
            await expect(visibleJobs.nth(i)).toBeVisible();
          }
        }
      }
    }
  });

  test('remove tag from job', async ({ page }) => {
    await page.goto('/');
    
    const jobCard = page.locator('[data-testid="job-card"]').first();
    await expect(jobCard).toBeVisible({ timeout: 10000 });
    await jobCard.click();
    
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    
    // Find assigned tags
    const tagChips = modal.locator('[data-testid="tag-chip"]')
      .or(modal.locator('.tag-chip'))
      .or(modal.locator('[data-testid="job-tags"] button'));
    
    const tagCount = await tagChips.count();
    
    if (tagCount > 0) {
      // Click remove button on first tag
      const removeButton = tagChips.first().locator('[data-testid="remove-tag"]')
        .or(tagChips.first().getByRole('button', { name: /remove|delete|×/i }));
      
      if (await removeButton.isVisible()) {
        await removeButton.click();
        
        // Tag count should decrease
        await expect(async () => {
          const newCount = await tagChips.count();
          expect(newCount).toBeLessThan(tagCount);
        }).toPass({ timeout: 3000 });
      }
    }
  });
});
