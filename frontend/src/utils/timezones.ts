const FALLBACK_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Australia/Sydney',
];

export function getSupportedTimeZones(): string[] {
  try {
    const intlObj = Intl as typeof Intl & { supportedValuesOf?: (value: string) => string[] };
    if (intlObj.supportedValuesOf) {
      return intlObj.supportedValuesOf('timeZone');
    }
  } catch {
    // ignore
  }
  return FALLBACK_TIMEZONES;
}

export function getBrowserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}
