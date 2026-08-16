import { createTheme, type MantineColorsTuple } from '@mantine/core';
import {
  colors,
  typography,
  radii,
  bluePalette,
  successPalette,
  warningPalette,
  dangerPalette,
} from './tokens';

/**
 * Mantine theme recreating the Figma design system (REQ-SHELL-02, D4).
 *
 * - primary `#2563EB` (exposed as the `blue` color, shade 6)
 * - Inter body / DM Sans headings
 * - semantic success/warning/danger palettes centered on the Figma hex values
 * - radius scale 6 / 10 / 14 / 18
 */
export const theme = createTheme({
  primaryColor: 'blue',
  primaryShade: 6,
  colors: {
    blue: bluePalette as unknown as MantineColorsTuple,
    success: successPalette as unknown as MantineColorsTuple,
    warning: warningPalette as unknown as MantineColorsTuple,
    danger: dangerPalette as unknown as MantineColorsTuple,
  },
  fontFamily: `${typography.body}, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
  fontFamilyMonospace:
    'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
  headings: {
    fontFamily: `${typography.headings}, ${typography.body}, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
    fontWeight: '600',
    sizes: {
      h1: { fontSize: '2rem', lineHeight: '1.2' },
      h2: { fontSize: '1.5rem', lineHeight: '1.25' },
      h3: { fontSize: '1.25rem', lineHeight: '1.3' },
      h4: { fontSize: '1.125rem', lineHeight: '1.35' },
      h5: { fontSize: '1rem', lineHeight: '1.4' },
      h6: { fontSize: '0.875rem', lineHeight: '1.4' },
    },
  },
  radius: {
    xs: radii.sm,
    sm: radii.md,
    md: radii.lg,
    lg: radii.xl,
    xl: radii.xl,
  },
  defaultRadius: 'md',
  breakpoints: {
    xs: '36em',
    sm: '48em',
    md: '64em',
    lg: '75em',
    xl: '88em',
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '24px',
  },
  components: {
    Card: {
      defaultProps: {
        radius: 'md',
      },
    },
    Paper: {
      defaultProps: {
        radius: 'md',
      },
    },
    Table: {
      defaultProps: {
        highlightOnHover: true,
      },
    },
    Button: {
      defaultProps: {
        radius: 'md',
      },
    },
    TextInput: {
      defaultProps: {
        radius: 'md',
      },
    },
    PasswordInput: {
      defaultProps: {
        radius: 'md',
      },
    },
    Select: {
      defaultProps: {
        radius: 'md',
      },
    },
    Textarea: {
      defaultProps: {
        radius: 'md',
      },
    },
    NumberInput: {
      defaultProps: {
        radius: 'md',
      },
    },
    Modal: {
      defaultProps: {
        radius: 'lg',
      },
    },
    Badge: {
      defaultProps: {
        radius: 'sm',
      },
    },
  },
});

/** Figma primary color re-exported for direct consumption in tests/components. */
export const primaryColor = colors.primary;
