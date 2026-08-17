/** Minimalist Modern design tokens. */
export const colors = {
  primary: '#0052FF',
  primaryLight: '#4D7CFF',
  backgroundApp: '#FAFAFA',
  backgroundSurface: '#FFFFFF',
  backgroundMuted: '#F1F5F9',
  textPrimary: '#0F172A',
  textSecondary: '#64748B',
  textMuted: '#94A3B8',
  border: '#E2E8F0',
  success: '#16A34A',
  warning: '#D97706',
  danger: '#DC2626',
  dark: '#0F172A',
} as const;

export const typography = {
  body: 'Inter',
  headings: 'Calistoga',
  mono: 'JetBrains Mono',
} as const;

export const radii = {
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '20px',
} as const;

export const radiiValues = ['8', '12', '16', '20'] as const;

export const bluePalette = [
  '#EEF4FF', '#DCE8FF', '#BDD1FF', '#91B0FF', '#6B8FFF',
  '#4D7CFF', '#0052FF', '#0047DE', '#0039B8', '#002D91',
] as const;

export const successPalette = [
  '#F0FDF4', '#DCFCE7', '#BBF7D0', '#86EFAC', '#4ADE80',
  '#22C55E', '#16A34A', '#15803D', '#166534', '#14532D',
] as const;

export const warningPalette = [
  '#FFFBEB', '#FEF3C7', '#FDE68A', '#FCD34D', '#FBBF24',
  '#F59E0B', '#D97706', '#B45309', '#92400E', '#78350F',
] as const;

export const dangerPalette = [
  '#FEF2F2', '#FEE2E2', '#FECACA', '#FCA5A5', '#F87171',
  '#EF4444', '#DC2626', '#B91C1C', '#991B1B', '#7F1D1D',
] as const;
