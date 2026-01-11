import React, { useEffect, useRef } from 'react';

declare global {
  interface Window {
    turnstile?: {
      render: (
        el: HTMLElement,
        options: {
          sitekey: string;
          callback: (token: string) => void;
          'error-callback'?: () => void;
          'expired-callback'?: () => void;
        }
      ) => unknown;
      remove?: (widgetId: unknown) => void;
    };
  }
}

interface TurnstileWidgetProps {
  siteKey: string;
  onToken: (token: string) => void;
  onError?: (message: string) => void;
}

export const TurnstileWidget: React.FC<TurnstileWidgetProps> = ({ siteKey, onToken, onError }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetRef = useRef<unknown>(null);

  useEffect(() => {
    let cancelled = false;

    const renderWidget = () => {
      if (cancelled || !containerRef.current || !window.turnstile) {
        return;
      }
      try {
        widgetRef.current = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          callback: (token: string) => onToken(token),
          'error-callback': () => onError?.('CAPTCHA failed. Please try again.'),
          'expired-callback': () => onToken(''),
        });
      } catch {
        onError?.('CAPTCHA could not be rendered.');
      }
    };

    const ensureScript = () => {
      if (typeof window === 'undefined') return;
      if (window.turnstile) {
        renderWidget();
        return;
      }

      const existing = document.querySelector<HTMLScriptElement>('script[data-selenite="turnstile"]');
      if (existing) {
        existing.addEventListener('load', renderWidget, { once: true });
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
      script.async = true;
      script.defer = true;
      script.dataset.selenite = 'turnstile';
      script.onload = renderWidget;
      script.onerror = () => onError?.('Failed to load CAPTCHA.');
      document.head.appendChild(script);
    };

    ensureScript();

    return () => {
      cancelled = true;
      if (window.turnstile && widgetRef.current && typeof window.turnstile.remove === 'function') {
        window.turnstile.remove(widgetRef.current);
      }
    };
  }, [siteKey, onError, onToken]);

  return <div ref={containerRef} className="min-h-[60px]" />;
};
