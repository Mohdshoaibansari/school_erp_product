import { describe, expect, it } from 'vitest';
import { primaryColor, theme } from '../index';
import { radiiValues } from '../tokens';

describe('theme', () => {
  it('primary color resolves to #0052FF (REQ-SHELL-02)', () => {
    expect(theme.primaryColor).toBe('blue');
    expect(theme.colors?.blue?.[6]).toBe('#0052FF');
    expect(primaryColor).toBe('#0052FF');
  });

  it('uses Inter body and Calistoga headings (REQ-SHELL-02)', () => {
    expect(theme.fontFamily).toContain('Inter');
    expect(theme.headings?.fontFamily).toContain('Calistoga');
  });

  it('exposes the radius scale 8/12/16/20', () => {
    expect(radiiValues).toEqual(['8', '12', '16', '20']);
  });

  it('exposes semantic colors', () => {
    expect(theme.colors?.success?.[6]).toBe('#16A34A');
    expect(theme.colors?.warning?.[6]).toBe('#D97706');
    expect(theme.colors?.danger?.[6]).toBe('#DC2626');
  });
});
