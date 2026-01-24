export type DateFormat = 'locale' | 'mdy' | 'dmy' | 'ymd';
export type TimeFormat = 'locale' | '12h' | '24h';

export type DateTimePreferences = {
  timeZone?: string | null;
  dateFormat?: DateFormat;
  timeFormat?: TimeFormat;
  locale?: string | null;
  includeSeconds?: boolean;
  includeTimeZoneName?: boolean;
  includeTime?: boolean;
  includeDate?: boolean;
};

type DateInput = string | number | Date | null | undefined;

const DEFAULT_DATE_FORMAT: DateFormat = 'locale';
const DEFAULT_TIME_FORMAT: TimeFormat = 'locale';

const parseAsUTC = (value: string): Date | null => {
  if (!value) return null;
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value);
  const normalized = hasZone ? value : `${value}Z`;
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};

const resolveDate = (value: DateInput): Date | null => {
  if (!value) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === 'number') {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  if (typeof value === 'string') {
    return parseAsUTC(value);
  }
  return null;
};

const formatDatePart = (
  date: Date,
  locale: string | undefined,
  timeZone: string | undefined,
  dateFormat: DateFormat
): string => {
  if (dateFormat === 'locale') {
    return new Intl.DateTimeFormat(locale, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone,
    }).format(date);
  }

  const parts = new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone,
  }).formatToParts(date);
  const find = (type: string) => parts.find((part) => part.type === type)?.value || '';
  const year = find('year');
  const month = find('month');
  const day = find('day');
  if (dateFormat === 'mdy') {
    return `${month}/${day}/${year}`;
  }
  if (dateFormat === 'dmy') {
    return `${day}/${month}/${year}`;
  }
  return `${year}-${month}-${day}`;
};

const formatTimePart = (
  date: Date,
  locale: string | undefined,
  timeZone: string | undefined,
  timeFormat: TimeFormat,
  includeSeconds: boolean,
  includeTimeZoneName: boolean
): string => {
  return new Intl.DateTimeFormat(locale, {
    hour: 'numeric',
    minute: '2-digit',
    second: includeSeconds ? '2-digit' : undefined,
    hour12: timeFormat === '12h' ? true : timeFormat === '24h' ? false : undefined,
    timeZone,
    timeZoneName: includeTimeZoneName ? 'short' : undefined,
  }).format(date);
};

export const formatDateTime = (value: DateInput, preferences: DateTimePreferences = {}): string => {
  const date = resolveDate(value);
  if (!date) return 'Unknown';

  const {
    timeZone = null,
    dateFormat = DEFAULT_DATE_FORMAT,
    timeFormat = DEFAULT_TIME_FORMAT,
    locale,
    includeSeconds = false,
    includeTimeZoneName = false,
    includeTime = true,
    includeDate = true,
  } = preferences;

  const resolvedLocale = locale || undefined;
  const resolvedTimeZone = timeZone || undefined;

  const datePart = includeDate
    ? formatDatePart(date, resolvedLocale, resolvedTimeZone, dateFormat)
    : '';
  const timePart = includeTime
    ? formatTimePart(
        date,
        resolvedLocale,
        resolvedTimeZone,
        timeFormat,
        includeSeconds,
        includeTimeZoneName
      )
    : '';

  if (datePart && timePart) {
    return `${datePart}, ${timePart}`;
  }
  return datePart || timePart || 'Unknown';
};
