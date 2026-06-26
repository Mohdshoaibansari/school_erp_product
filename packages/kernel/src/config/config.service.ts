import { PrismaClient, ConfigValue, ConfigKey, ConfigValueType } from '@school-erp/database';

export interface GetConfigOptions {
  tenantId?: string;
  institutionId?: string;
}

export interface SetConfigInput {
  configKeyCode: string;
  value: string;
  tenantId?: string;
  institutionId?: string;
}

export class ConfigService {
  constructor(private prisma: PrismaClient) {}

  async get(
    configKeyCode: string,
    options: GetConfigOptions = {}
  ): Promise<{ value: string; scope: string } | null> {
    const { tenantId, institutionId } = options;

    // First, get the config key
    const configKey = await this.prisma.configKey.findUnique({
      where: { code: configKeyCode },
    });

    if (!configKey) {
      throw new Error(`Config key "${configKeyCode}" not found`);
    }

    // Try institution-level first (most specific)
    if (institutionId) {
      const institutionValue = await this.prisma.configValue.findFirst({
        where: {
          configKeyId: configKey.id,
          institutionId,
        },
      });

      if (institutionValue) {
        return { value: institutionValue.value, scope: 'institution' };
      }
    }

    // Try tenant-level
    if (tenantId) {
      const tenantValue = await this.prisma.configValue.findFirst({
        where: {
          configKeyId: configKey.id,
          tenantId,
          institutionId: null,
        },
      });

      if (tenantValue) {
        return { value: tenantValue.value, scope: 'tenant' };
      }
    }

    // Try platform-level (default)
    const platformValue = await this.prisma.configValue.findFirst({
      where: {
        configKeyId: configKey.id,
        tenantId: null,
        institutionId: null,
      },
    });

    if (platformValue) {
      return { value: platformValue.value, scope: 'platform' };
    }

    return null;
  }

  async set(input: SetConfigInput): Promise<ConfigValue> {
    const { configKeyCode, value, tenantId, institutionId } = input;

    // First, get the config key
    const configKey = await this.prisma.configKey.findUnique({
      where: { code: configKeyCode },
    });

    if (!configKey) {
      throw new Error(`Config key "${configKeyCode}" not found`);
    }

    // Validate value type
    this.validateValueType(value, configKey.valueType);

    // Upsert the config value
    return this.prisma.configValue.upsert({
      where: {
        configKeyId_tenantId_institutionId: {
          configKeyId: configKey.id,
          tenantId: tenantId || null,
          institutionId: institutionId || null,
        },
      },
      update: { value },
      create: {
        configKeyId: configKey.id,
        tenantId: tenantId || null,
        institutionId: institutionId || null,
        value,
      },
    });
  }

  async createConfigKey(data: {
    code: string;
    name: string;
    description?: string;
    valueType: ConfigValueType;
  }): Promise<ConfigKey> {
    return this.prisma.configKey.create({
      data,
    });
  }

  async getConfigKeys(): Promise<ConfigKey[]> {
    return this.prisma.configKey.findMany({
      orderBy: { code: 'asc' },
    });
  }

  async getConfigValues(
    configKeyCode: string,
    options: GetConfigOptions = {}
  ): Promise<ConfigValue[]> {
    const configKey = await this.prisma.configKey.findUnique({
      where: { code: configKeyCode },
    });

    if (!configKey) {
      throw new Error(`Config key "${configKeyCode}" not found`);
    }

    return this.prisma.configValue.findMany({
      where: {
        configKeyId: configKey.id,
        ...(options.tenantId ? { tenantId: options.tenantId } : {}),
        ...(options.institutionId ? { institutionId: options.institutionId } : {}),
      },
    });
  }

  private validateValueType(value: string, valueType: ConfigValueType): void {
    switch (valueType) {
      case 'NUMBER':
        if (isNaN(Number(value))) {
          throw new Error(`Value "${value}" is not a valid number`);
        }
        break;
      case 'BOOLEAN':
        if (!['true', 'false', '1', '0'].includes(value.toLowerCase())) {
          throw new Error(`Value "${value}" is not a valid boolean`);
        }
        break;
      case 'JSON':
        try {
          JSON.parse(value);
        } catch {
          throw new Error(`Value "${value}" is not valid JSON`);
        }
        break;
      case 'STRING':
      default:
        // Strings are always valid
        break;
    }
  }

  parseValue(value: string, valueType: ConfigValueType): any {
    switch (valueType) {
      case 'NUMBER':
        return Number(value);
      case 'BOOLEAN':
        return ['true', '1'].includes(value.toLowerCase());
      case 'JSON':
        return JSON.parse(value);
      case 'STRING':
      default:
        return value;
    }
  }
}
