import { describe, expect, it } from 'vitest';
import { primaryColor, theme } from '../index';
import { radiiValues } from '../tokens';

describe('theme', () => {
  it('primary color resolves to #2563EB (REQ-SHELL-02)', () => {
    expect(theme.primaryColor).toBe('blue');
    expect(theme.colors?.blue?.[6]).toBe('#2563EB');
    expect(primaryColor).toBe('#2563EB');
  });

  it('uses Inter body and DM Sans headings (REQ-SHELL-02)', () => {
    expect(theme.fontFamily).toContain('Inter');
    expect(theme.headings?.fontFamily).toContain('DM Sans');
  });

  it('exposes the Figma radius scale 6/10/14/18', () => {
    expect(radiiValues).toEqual(['6', '10', '14', '18']);
  });

  it('exposes semantic colors', () => {
    expect(theme.colors?.success?.[6]).toBe('#16A34A');
    expect(theme.colors?.warning?.[6]).toBe('#D97706');
    expect(theme.colors?.danger?.[6]).toBe('#DC2626');
  });
});
