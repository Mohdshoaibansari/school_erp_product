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

export const theme = createTheme({
  primaryColor: 'blue',
  primaryShade: 6,
  colors: {
    blue: bluePalette as unknown as MantineColorsTuple,
    success: successPalette as unknown as MantineColorsTuple,
    warning: warningPalette as unknown as MantineColorsTuple,
    danger: dangerPalette as unknown as MantineColorsTuple,
  },
  fontFamily: `${typography.body}, system-ui, sans-serif`,
  fontFamilyMonospace: `${typography.mono}, ui-monospace, SFMono-Regular, monospace`,
  headings: {
    fontFamily: `${typography.headings}, Georgia, serif`,
    fontWeight: '400',
    sizes: {
      h1: { fontSize: '2.75rem', lineHeight: '1.08' },
      h2: { fontSize: '2rem', lineHeight: '1.15' },
      h3: { fontSize: '1.5rem', lineHeight: '1.2' },
      h4: { fontSize: '1.25rem', lineHeight: '1.25' },
      h5: { fontSize: '1rem', lineHeight: '1.35' },
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
  breakpoints: { xs: '36em', sm: '48em', md: '64em', lg: '75em', xl: '88em' },
  spacing: { xs: '6px', sm: '10px', md: '14px', lg: '20px', xl: '28px' },
  components: {
    Card: { defaultProps: { radius: 'md' } },
    Paper: { defaultProps: { radius: 'md' } },
    Table: { defaultProps: { highlightOnHover: true } },
    Button: { defaultProps: { radius: 'md' } },
    TextInput: { defaultProps: { radius: 'md' } },
    PasswordInput: { defaultProps: { radius: 'md' } },
    Select: { defaultProps: { radius: 'md' } },
    Textarea: { defaultProps: { radius: 'md' } },
    NumberInput: { defaultProps: { radius: 'md' } },
    Modal: { defaultProps: { radius: 'lg' } },
    Badge: { defaultProps: { radius: 'xl' } },
  },
});

export const primaryColor = colors.primary;
