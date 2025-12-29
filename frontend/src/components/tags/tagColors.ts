export const TAG_COLOR_PALETTE = [
  '#000000', // Black
  '#FFD700', // Gold
  '#228B22', // Forest Green
  '#4169E1', // Royal Blue
  '#E34234', // Vermillion
  '#F0EAD6', // Eggshell White
  '#FF8C00', // Dark Orange
  '#FF00FF', // Magenta
];

const normalizeTagColor = (color?: string | null) => {
  if (!color) return null;
  const trimmed = color.trim();
  return trimmed ? trimmed : null;
};

const hashTagSeed = (value: string) => {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0;
  }
  return hash;
};

const parseHexColor = (value: string) => {
  const normalized = value.replace('#', '');
  if (normalized.length !== 6) return null;
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  if ([r, g, b].some((channel) => Number.isNaN(channel))) {
    return null;
  }
  return { r, g, b };
};

export const getTagColor = (
  tag: { color?: string | null; id?: number | null; name?: string | null },
  palette: string[] = TAG_COLOR_PALETTE
) => {
  const normalized = normalizeTagColor(tag.color);
  if (normalized) return normalized;
  const seed = typeof tag.id === 'number' ? tag.id : hashTagSeed(tag.name ?? '');
  const index = Math.abs(seed) % palette.length;
  return palette[index] ?? palette[0];
};

export const getTagTextColor = (background: string) => {
  const parsed = parseHexColor(background);
  if (!parsed) return '#000000';
  const brightness = (parsed.r * 299 + parsed.g * 587 + parsed.b * 114) / 1000;
  return brightness >= 140 ? '#000000' : '#FFFFFF';
};

export const pickTagColor = (existing: Array<{ color?: string | null }>, fallback?: string) => {
  const used = new Set(existing.map((tag) => normalizeTagColor(tag.color)).filter(Boolean));
  for (const color of TAG_COLOR_PALETTE) {
    if (!used.has(color)) {
      return color;
    }
  }
  return fallback ?? TAG_COLOR_PALETTE[0];
};
