import { SubscriptionService } from './subscription.service';

export interface EntitlementCheckResult {
  allowed: boolean;
  reason?: string;
}

export class EntitlementMiddleware {
  constructor(private subscriptionService: SubscriptionService) {}

  async checkModuleAccess(
    tenantId: string,
    moduleCode: string
  ): Promise<EntitlementCheckResult> {
    const isAvailable = await this.subscriptionService.isModuleAvailable(
      tenantId,
      moduleCode
    );

    if (!isAvailable) {
      return {
        allowed: false,
        reason: `Module '${moduleCode}' is not available in your subscription tier`,
      };
    }

    return { allowed: true };
  }

  async checkStudentLimit(
    tenantId: string
  ): Promise<EntitlementCheckResult> {
    const capCheck = await this.subscriptionService.checkStudentCap(tenantId);

    if (!capCheck.allowed) {
      return {
        allowed: false,
        reason: `Student limit reached (${capCheck.current}/${capCheck.cap}). Please upgrade your subscription.`,
      };
    }

    return { allowed: true };
  }

  // Express middleware factory
  requireModule(moduleCode: string) {
    return async (req: any, res: any, next: any) => {
      const tenantId = req.tenantId;
      if (!tenantId) {
        return res.status(401).json({ error: 'Tenant not identified' });
      }

      const result = await this.checkModuleAccess(tenantId, moduleCode);
      if (!result.allowed) {
        return res.status(403).json({ error: result.reason });
      }

      next();
    };
  }

  // Express middleware factory for student limit
  requireStudentCapacity() {
    return async (req: any, res: any, next: any) => {
      const tenantId = req.tenantId;
      if (!tenantId) {
        return res.status(401).json({ error: 'Tenant not identified' });
      }

      const result = await this.checkStudentLimit(tenantId);
      if (!result.allowed) {
        return res.status(403).json({ error: result.reason });
      }

      next();
    };
  }
}

// Helper function to create entitlement middleware
export function createEntitlementMiddleware(
  subscriptionService: SubscriptionService
): EntitlementMiddleware {
  return new EntitlementMiddleware(subscriptionService);
}
