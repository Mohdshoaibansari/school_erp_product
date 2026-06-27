export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function isValidPhone(phone: string): boolean {
  return /^[6-9]\d{9}$/.test(phone);
}

export function isRequired(value: unknown, fieldName: string): void {
  if (value === undefined || value === null || (typeof value === 'string' && value.trim() === '')) {
    throw new Error(`${fieldName} is required`);
  }
}

export function isValidDateRange(start: Date, end: Date): boolean {
  return start <= end;
}
