/**
 * Figma design-system tokens (D4, REQ-SHELL-02).
 *
 * These are the single source of truth for the visual system. The Mantine
 * theme in `theme/index.ts` maps these constants into `createTheme(...)`.
 * No new design invention: every screen reuses these tokens.
 */

export const colors = {
  /** Primary brand color (Figma primary). */
  primary: '#2563EB',

  /** Backgrounds. */
  backgroundApp: '#F1F5F9',
  backgroundSurface: '#FFFFFF',

  /** Text. */
  textPrimary: '#0F172A',
  textSecondary: '#475569',
  textMuted: '#94A3B8',

  /** Semantic. */
  success: '#16A34A',
  warning: '#D97706',
  danger: '#DC2626',
} as const;

export const typography = {
  body: 'Inter',
  headings: 'DM Sans',
} as const;

/** Radius scale (smallest → largest), per Figma. */
export const radii = {
  sm: '6px',
  md: '10px',
  lg: '14px',
  xl: '18px',
} as const;

export const radiiValues = ['6', '10', '14', '18'] as const;

/** Blue ramp centered on the primary color (shade 6 === primary). */
export const bluePalette = [
  '#EFF6FF',
  '#DBEAFE',
  '#BFDBFE',
  '#93C5FD',
  '#60A5FA',
  '#3B82F6',
  '#2563EB',
  '#1D4ED8',
  '#1E40AF',
  '#1E3A8A',
] as const;

export const successPalette = [
  '#F0FDF4',
  '#DCFCE7',
  '#BBF7D0',
  '#86EFAC',
  '#4ADE80',
  '#22C55E',
  '#16A34A',
  '#15803D',
  '#166534',
  '#14532D',
] as const;

export const warningPalette = [
  '#FFFBEB',
  '#FEF3C7',
  '#FDE68A',
  '#FCD34D',
  '#FBBF24',
  '#F59E0B',
  '#D97706',
  '#B45309',
  '#92400E',
  '#78350F',
] as const;

export const dangerPalette = [
  '#FEF2F2',
  '#FEE2E2',
  '#FECACA',
  '#FCA5A5',
  '#F87171',
  '#EF4444',
  '#DC2626',
  '#B91C1C',
  '#991B1B',
  '#7F1D1D',
] as const;
