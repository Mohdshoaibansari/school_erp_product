export interface TierConfig {
  name: string;
  description: string;
  studentCap: number | null;
  modules: { code: string; enabled: boolean }[];
}

export const FREE_TIER: TierConfig = {
  name: 'Free',
  description: 'Free tier with basic modules and 100 student limit',
  studentCap: 100,
  modules: [
    { code: 'students', enabled: true },
    { code: 'attendance', enabled: true },
    { code: 'fees', enabled: true },
  ],
};

export const PAID_TIER: TierConfig = {
  name: 'Paid',
  description: 'Paid tier with all modules and unlimited students',
  studentCap: null,
  modules: [
    { code: 'students', enabled: true },
    { code: 'attendance', enabled: true },
    { code: 'fees', enabled: true },
    { code: 'exams', enabled: true },
    { code: 'homework', enabled: true },
    { code: 'library', enabled: true },
    { code: 'transport', enabled: true },
    { code: 'inventory', enabled: true },
    { code: 'payroll', enabled: true },
    { code: 'communication', enabled: true },
  ],
};

export const DEFAULT_TIERS: TierConfig[] = [
  FREE_TIER,
  PAID_TIER,
];
