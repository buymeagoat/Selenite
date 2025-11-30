export const isDevelopment = () => import.meta.env.DEV === true;

type ConsoleMethod = 'log' | 'info' | 'warn' | 'error';

function createDevLogger(method: ConsoleMethod) {
  return (...args: unknown[]) => {
    if (isDevelopment()) {
      // eslint-disable-next-line no-console
      console[method](...args);
    }
  };
}

export const devLog = createDevLogger('log');
export const devInfo = createDevLogger('info');
export const devWarn = createDevLogger('warn');
export const devError = createDevLogger('error');
