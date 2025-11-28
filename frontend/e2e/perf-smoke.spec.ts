import { test, expect } from '@playwright/test';

test('Health endpoint responds quickly', async ({ request }) => {
  const start = Date.now();
  const response = await request.get('/health');
  const elapsed = Date.now() - start;
  expect(response.ok()).toBeTruthy();
  expect(elapsed).toBeLessThanOrEqual(500);
});
