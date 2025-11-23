import { injectAxe, getViolations } from 'axe-playwright';

export async function runAxe(page: import('@playwright/test').Page, context: string) {
  await injectAxe(page);
  const violations = await getViolations(page, undefined, {
    detailedReport: true,
    detailedReportOptions: { html: true },
  });
  if (violations.length) {
    console.error(`Accessibility violations on ${context}:`, JSON.stringify(violations, null, 2));
  }
  return violations;
}
