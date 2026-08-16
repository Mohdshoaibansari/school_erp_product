const LAST_INSTITUTION_KEY = 'erp.last_institution_id';

export function loadLastUsedInstitution(): string | null {
  if (typeof window === 'undefined') return null;
  return window.sessionStorage.getItem(LAST_INSTITUTION_KEY);
}

export function persistLastUsedInstitution(id: string | null): void {
  if (typeof window === 'undefined') return;
  if (id) {
    window.sessionStorage.setItem(LAST_INSTITUTION_KEY, id);
  } else {
    window.sessionStorage.removeItem(LAST_INSTITUTION_KEY);
  }
}

/**
 * R4: default to the last-used institution (persisted); fall back to the
 * first institution in the list when none is remembered.
 */
export function resolveDefaultInstitution(
  institutions: ReadonlyArray<{ id: string }>,
  lastUsed: string | null,
): string | null {
  if (lastUsed && institutions.some((i) => i.id === lastUsed)) {
    return lastUsed;
  }
  return institutions[0]?.id ?? null;
}
