import { vi } from 'vitest';
import '@testing-library/jest-dom';

// Vitest setupFiles run outside the test environment globals unless imported.
// Use direct execution with spies instead of beforeAll/afterAll.

if (typeof window !== 'undefined') {
  if (!('alert' in window)) {
    // @ts-ignore
    window.alert = () => {};
  }
  if (!('prompt' in window)) {
    // @ts-ignore
    window.prompt = () => '';
  }
  if (!('confirm' in window)) {
    // @ts-ignore
    window.confirm = () => true;
  }
  if (!('isAlertMocked' in (window as any))) {
    vi.spyOn(window, 'alert').mockImplementation(() => {});
    vi.spyOn(window, 'prompt').mockImplementation(() => 'test');
    vi.spyOn(window, 'confirm').mockImplementation(() => true);
    (window as any).isAlertMocked = true;
  }
}

